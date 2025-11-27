add_library(alinify_gpu_warp STATIC
    cuda_warper.cpp
)

target_include_directories(alinify_gpu_warp PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(alinify_gpu_warp PUBLIC
    alinify_core
    ${TORCH_LIBRARIES}
)

# Enable CUDA if available
if(USE_CUDA)
    set_target_properties(alinify_gpu_warp PROPERTIES
        CUDA_SEPARABLE_COMPILATION ON
    )
endif()
