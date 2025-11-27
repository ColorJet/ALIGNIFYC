add_library(alinify_camera STATIC
    gidel_camera.cpp
)

target_include_directories(alinify_camera PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(alinify_camera PUBLIC
    alinify_core
    ProcFgApi
    InfiniVision
    Proc
)
