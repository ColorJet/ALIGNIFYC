if(BUILD_PYTHON_BINDINGS)
    pybind11_add_module(alinify_bindings
        bindings.cpp
    )
    
    target_link_libraries(alinify_bindings PRIVATE
        alinify_core
        alinify_camera
        alinify_stitching
        alinify_preprocessing
        # alinify_registration  # Disabled until ITK is available
        # alinify_gpu_warp  # Disabled until CUDA is available
        alinify_printer
    )
    
    # Install to Python site-packages or local directory
    install(TARGETS alinify_bindings
        LIBRARY DESTINATION ${CMAKE_SOURCE_DIR}/gui
    )
endif()
