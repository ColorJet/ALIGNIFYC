add_library(alinify_printer STATIC
    printer_interface.cpp
)

target_include_directories(alinify_printer PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(alinify_printer PUBLIC
    alinify_core
)
