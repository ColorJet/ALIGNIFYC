add_library(alinify_stitching STATIC
    strip_stitcher.cpp
)

target_include_directories(alinify_stitching PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(alinify_stitching PUBLIC
    alinify_core
    ${OpenCV_LIBS}
)
