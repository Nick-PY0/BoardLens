#!/bin/sh
set -eu
# Run against the expanded LC0 corresponding source, including pinned subprojects.
# NDK r27+, Python 3.12 + Meson/Ninja; LC0 v0.32.1, common b326b154.
: "${ANDROID_NDK_HOME:?Set Android NDK directory}"
: "${LC0_SOURCE:?Set expanded LC0 source directory}"
build_dir="${LC0_BUILD:-./lc0-android-build}"
ndk_host=linux-x86_64
[ "$(uname -s)" != Darwin ] || ndk_host=darwin-x86_64
ndk_bin="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/$ndk_host/bin"
mkdir -p "$build_dir"
cat > "$build_dir/cross.ini" <<CONFIG
[binaries]
c = '$ndk_bin/aarch64-linux-android29-clang'
cpp = '$ndk_bin/aarch64-linux-android29-clang++'
ar = '$ndk_bin/llvm-ar'
strip = '$ndk_bin/llvm-strip'
[host_machine]
system = 'android'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'
[built-in options]
cpp_link_args = ['-static-libstdc++','-Wl,-z,max-page-size=16384','-Wl,-z,common-page-size=16384']
CONFIG
meson setup "$build_dir/build" "$LC0_SOURCE" --cross-file "$build_dir/cross.ini" --buildtype=release -Dnative_arch=false -Dopenblas=false -Daccelerate=false -Dmetal=disabled -Dplain_cuda=false -Donnx=false -Dispc=false -Ddefault_backend=eigen
ninja -C "$build_dir/build" -j3 lc0
"$ndk_bin/llvm-strip" --strip-debug "$build_dir/build/lc0"
cp "$build_dir/build/lc0" "$build_dir/liblc0.so"
