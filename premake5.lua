project "Opus"
    language "C"
    kind "StaticLib"

	staticruntime "off"

	targetdir ("%{wks.location}/bin/" .. outputDir .. "/%{prj.name}")
	objdir ("%{wks.location}/bin-int/" .. outputDir .. "/%{prj.name}")

    files {
        "src/**.c",
        "celt/**.c",
        "celt/**.h",
        "silk/**.c",
        "silk/**.h",
        "dnn/**.c",
        "dnn/**.h"
    }

    defines {
        "USE_ALLOCA"
    }

    includedirs {
        "include",
        "celt",
        "dnn",
        "silk"
    }

    excludes {
        "celt/arm/**.c",
        "silk/arm/**.c",
        "dnn/arm/**.c"
    }

    filter "configurations:Debug"
        defines { "DEBUG" }
        symbols "On"

    filter "configurations:Release"
        defines { "NDEBUG" }
        optimize "On"

    filter "system:windows"
        systemversion "latest"