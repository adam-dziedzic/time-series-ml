#!/bin/bash -e
#
#  Copyright (c) 2014, Facebook, Inc.
#  All rights reserved.
#
#  This source code is licensed under the BSD-style license found in the
#  LICENSE file in the root directory of this source tree. An additional grant
#  of patent rights can be found in the PATENTS file in the same directory.
#

echo
echo This script will install fblualib and all its dependencies.
echo It has been tested on Ubuntu 13.10 and Ubuntu 14.04, Linux x86_64.
echo

set -e
set -x

if [[ $(arch) != 'x86_64' ]]; then
    echo "x86_64 required" >&2
    exit 1
fi

issue=$(cat /etc/issue)
extra_packages=
if [[ $issue =~ ^Ubuntu\ 13\.10 ]]; then
    :
elif [[ $issue =~ ^Ubuntu\ 14 ]]; then
    extra_packages=libiberty-dev
elif [[ $issue =~ ^Ubuntu\ 16 ]]; then
    extra_packages=libiberty-dev
    echo "Trying to install on ubuntu 16.04"
    echo
else
    echo "Ubuntu 13.10 or 14.* required" >&2
    exit 1
fi

dir=$(mktemp --tmpdir -d fblualib-build.XXXXXX)

echo Working in $dir
echo
cd $dir

echo Installing required packages
echo
sudo apt-get install -y \
    git \
    curl \
    wget \
    g++ \
    automake \
    autoconf \
    autoconf-archive \
    libtool \
    libboost1.55-all-dev \
    libevent-dev \
    libdouble-conversion-dev \
    libgoogle-glog-dev \
    libgflags-dev \
    liblz4-dev \
    liblzma-dev \
    libsnappy-dev \
    make \
    zlib1g-dev \
    binutils-dev \
    libjemalloc-dev \
    $extra_packages \
    flex \
    bison \
    libkrb5-dev \
    libsasl2-dev \
    libnuma-dev \
    pkg-config \
    libssl-dev \
    libedit-dev \
    libmatio-dev \
    libpython-dev \
    libpython3-dev \
    python-numpy

echo
echo Cloning repositories
echo
git clone -b v0.35.0  --depth 1 https://github.com/facebook/folly.git
git clone -b v0.24.0  --depth 1 https://github.com/facebook/fbthrift.git
git clone https://github.com/facebook/thpp
git clone https://github.com/soumith/fblualib

echo
echo Building folly
echo

cd $dir/folly/folly
autoreconf -ivf
./configure
make
sudo make install
sudo ldconfig # reload the lib paths after freshly installed folly. fbthrift needs it.

echo
echo Building fbthrift
echo

cd $dir/fbthrift/thrift
autoreconf -ivf
./configure
make
sudo make install

echo
echo 'Installing TH++'
echo

cd $dir/thpp/thpp
./build.sh

echo
echo 'Installing FBLuaLib'
echo

cd $dir/fblualib/fblualib
./build.sh

echo
echo 'All done!'
echo