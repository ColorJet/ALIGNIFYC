# Stub implementations for preprocessing and registration
# These would be fully implemented with ITK/Elastix

add_library(alinify_preprocessing STATIC
    image_processor.cpp
)

target_include_directories(alinify_preprocessing PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(alinify_preprocessing PUBLIC
    alinify_core
    ${ITK_LIBRARIES}
    ${OpenCV_LIBS}
)
