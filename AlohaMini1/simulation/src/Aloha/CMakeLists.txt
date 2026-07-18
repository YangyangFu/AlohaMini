cmake_minimum_required(VERSION 3.5)
project(aloha)
 
# Default to C99
if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()
 
# Default to C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()
 
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()
 
# find dependencies
find_package(ament_cmake REQUIRED)
find_program(XACRO_EXECUTABLE xacro REQUIRED)
# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)
 
if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # uncomment the line when a copyright and license is not present in all source files
  #set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # uncomment the line when this package is not in a git repo
  #set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()
 
 
set(VISUAL_URDF "${CMAKE_CURRENT_BINARY_DIR}/Aloha.visual.urdf")
add_custom_command(
  OUTPUT "${VISUAL_URDF}"
  COMMAND "${XACRO_EXECUTABLE}"
          "${CMAKE_CURRENT_SOURCE_DIR}/urdf/aloha_visual.urdf.xacro"
          -o "${VISUAL_URDF}"
  DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/urdf/aloha_visual.urdf.xacro"
    "${CMAKE_CURRENT_SOURCE_DIR}/urdf/aloha_description.xacro"
  COMMENT "Generating portable visualization URDF"
  VERBATIM
)
add_custom_target(generate_visual_urdf ALL DEPENDS "${VISUAL_URDF}")

install(DIRECTORY
  meshes urdf textures config launch rviz worlds
  DESTINATION share/${PROJECT_NAME}/
)
install(FILES "${VISUAL_URDF}" DESTINATION share/${PROJECT_NAME}/urdf)
ament_package()
