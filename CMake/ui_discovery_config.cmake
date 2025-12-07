# CMake integration for UI Discovery System
# Add this to the main CMakeLists.txt to build the UI discovery functionality

option(BUILD_UI_DISCOVERY "Build UI Discovery System" ON)

if(BUILD_UI_DISCOVERY)
    message(STATUS "Building UI Discovery System")
    
    # Find required libraries for UI interaction
    if(UNIX AND NOT APPLE)
        # Linux - need X11 libraries
        find_package(X11 REQUIRED)
        if(X11_FOUND)
            message(STATUS "Found X11 libraries for UI discovery")
            set(UI_DISCOVERY_LIBS ${X11_LIBRARIES} ${X11_XTest_LIB})
            set(UI_DISCOVERY_INCLUDES ${X11_INCLUDE_DIR})
        else()
            message(WARNING "X11 libraries not found, UI discovery will have limited functionality")
            set(BUILD_UI_DISCOVERY OFF)
        endif()
    elseif(WIN32)
        # Windows - use built-in APIs
        set(UI_DISCOVERY_LIBS user32)
        set(UI_DISCOVERY_INCLUDES "")
    else()
        message(WARNING "UI discovery not implemented for this platform")
        set(BUILD_UI_DISCOVERY OFF)
    endif()
    
    if(BUILD_UI_DISCOVERY)
        # Add UI discovery source files
        set(UI_DISCOVERY_SOURCES
            ui_discovery.cpp
            ui_discovery.h
        )
        
        # Create UI discovery library
        add_library(ui_discovery ${UI_DISCOVERY_SOURCES})
        
        # Link required libraries
        target_link_libraries(ui_discovery 
            ${UI_DISCOVERY_LIBS}
            nlohmann_json::nlohmann_json
        )
        
        # Include directories
        target_include_directories(ui_discovery PRIVATE 
            ${UI_DISCOVERY_INCLUDES}
            ${CMAKE_CURRENT_SOURCE_DIR}
        )
        
        # Set C++ standard
        target_compile_features(ui_discovery PRIVATE cxx_std_14)
        
        # Add preprocessor definitions
        if(UNIX AND NOT APPLE)
            target_compile_definitions(ui_discovery PRIVATE LINUX_UI_DISCOVERY=1)
        elseif(WIN32)
            target_compile_definitions(ui_discovery PRIVATE WINDOWS_UI_DISCOVERY=1)
        endif()
        
        # Install UI discovery library
        install(TARGETS ui_discovery
            LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
            ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
            RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
        )
        
        # Install headers
        install(FILES ui_discovery.h
            DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
        )
        
        message(STATUS "UI Discovery System configured successfully")
    endif()
else()
    message(STATUS "UI Discovery System disabled")
endif()

# Function to add UI discovery to existing targets
function(add_ui_discovery_to_target target_name)
    if(BUILD_UI_DISCOVERY)
        target_link_libraries(${target_name} ui_discovery)
        target_compile_definitions(${target_name} PRIVATE UI_DISCOVERY_ENABLED=1)
        message(STATUS "Added UI discovery to target: ${target_name}")
    endif()
endfunction()
