#!/bin/sh
set -eu
# Stockfish 19, edb0d9db6731067ec50ce619ff372b463bc4dd5d.
# Android NDK r27+; the model is downloaded separately and SHA-256 verified.
: "${ANDROID_NDK_HOME:?Set ANDROID_NDK_HOME to NDK r27+}"
cd "$(dirname "$0")"
mkdir -p build
cd build
tar -xzf ../Stockfish-edb0d9d-source.tar.gz --strip-components=1
cd src
host=linux-x86_64
[ "$(uname -s)" != Darwin ] || host=darwin-x86_64
compiler="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/$host/bin/aarch64-linux-android29-clang++"
make -j4 all ARCH=armv8 COMP=ndk CXX="$compiler" EXTRACXXFLAGS=-DNNUE_EMBEDDING_OFF EXTRALDFLAGS="-Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384" EXE=libstockfish.so
mkdir -p ../../../app/src/main/jniLibs/arm64-v8a
cp libstockfish.so ../../../app/src/main/jniLibs/arm64-v8a/
