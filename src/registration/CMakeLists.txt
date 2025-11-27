add_library(alinify_registration STATIC
    elastix_wrapper.cpp
)

target_include_directories(alinify_registration PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(alinify_registration PUBLIC
    alinify_core
    ${ITK_LIBRARIES}
)
