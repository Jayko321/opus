import os
import argparse
import numpy as np

import torch
from torch import nn
import torch.nn.functional as F
import tqdm

import fargan
from dataset import FARGANDataset

nb_features = 36
nb_used_features = 20

parser = argparse.ArgumentParser()

parser.add_argument('model', type=str, help='CELPNet model')
parser.add_argument('features', type=str, help='path to feature file in .f32 format')
parser.add_argument('output', type=str, help='path to output file (16-bit PCM)')

parser.add_argument('--cuda-visible-devices', type=str, help="comma separates list of cuda visible device indices, default: CUDA_VISIBLE_DEVICES", default=None)


model_group = parser.add_argument_group(title="model parameters")
model_group.add_argument('--cond-size', type=int, help="first conditioning size, default: 256", default=256)

args = parser.parse_args()

if args.cuda_visible_devices != None:
    os.environ['CUDA_VISIBLE_DEVICES'] = args.cuda_visible_devices


features_file = args.features
signal_file = args.output



device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")

checkpoint = torch.load(args.model, map_location='cpu')

model = fargan.FARGAN(*checkpoint['model_args'], **checkpoint['model_kwargs'])


model.load_state_dict(checkpoint['state_dict'], strict=False)

features = np.reshape(np.memmap(features_file, dtype='float32', mode='r'), (1, -1, nb_features))
lpc = features[:,4-1:-1,nb_used_features:]
features = features[:, :, :nb_used_features]
periods = np.round(50*features[:,:,nb_used_features-2]+100).astype('int')

nb_frames = features.shape[1]
#nb_frames = 1000
gamma = checkpoint['model_kwargs']['gamma']

def lpc_synthesis_one_frame(frame, filt, buffer, weighting_vector=np.ones(16)):
    
    out = np.zeros_like(frame)
    filt = np.flip(filt)
    
    inp = frame[:]
    
    
    for i in range(0, inp.shape[0]):
        
        s = inp[i] - np.dot(buffer*weighting_vector, filt)
        
        buffer[0] = s
        
        buffer = np.roll(buffer, -1)
        
        out[i] = s
        
    return out

def inverse_perceptual_weighting (pw_signal, filters, weighting_vector):
    
    #inverse perceptual weighting= H_preemph / W(z/gamma)
    
    signal = np.zeros_like(pw_signal)
    buffer = np.zeros(16)
    num_frames = pw_signal.shape[0] //160
    assert num_frames == filters.shape[0]
    for frame_idx in range(0, num_frames):
        
        in_frame = pw_signal[frame_idx*160: (frame_idx+1)*160][:]
        out_sig_frame = lpc_synthesis_one_frame(in_frame, filters[frame_idx, :], buffer, weighting_vector)
        signal[frame_idx*160: (frame_idx+1)*160] = out_sig_frame[:]
        buffer[:] = out_sig_frame[-16:]
    return signal



if __name__ == '__main__':
    model.to(device)
    features = torch.tensor(features).to(device)
    #lpc = torch.tensor(lpc).to(device)
    periods = torch.tensor(periods).to(device)
    
    sig, _ = model(features, periods, nb_frames - 4)
    weighting_vector = np.array([gamma**i for i in range(16,0,-1)])
    sig = sig.detach().numpy().flatten()
    sig = inverse_perceptual_weighting(sig, lpc[0,:,:], weighting_vector)
    
    pcm = np.round(32768*np.clip(sig, a_max=.99, a_min=-.99)).astype('int16')
    pcm.tofile(signal_file)