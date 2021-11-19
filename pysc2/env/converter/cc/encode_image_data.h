// Copyright 2021 DeepMind Technologies Ltd. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS-IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#ifndef PYSC2_ENV_CONVERTER_CC_ENCODE_IMAGE_DATA_H_
#define PYSC2_ENV_CONVERTER_CC_ENCODE_IMAGE_DATA_H_

#include <cstdint>
#include <functional>
#include <string>

#include "glog/logging.h"
#include "dm_env_rpc/v1/dm_env_rpc.pb.h"
#include "pysc2/env/converter/cc/tensor_util.h"
#include "s2clientprotocol/common.pb.h"

namespace pysc2 {

template <typename T>
void EncodeImageData1Bit(const SC2APIProtocol::ImageData& data,
                         dm_env_rpc::v1::Tensor* output) {
  int k = 0;
  int size = data.size().y();
  CHECK_GT(size, 0);
  MutableMatrix<T> m(output);
  CHECK_EQ(m.height(), data.size().x());
  CHECK_EQ(m.width(), data.size().y());
  CHECK_EQ(data.data().size() * 8, data.size().x() * data.size().y());
  for (char c : data.data()) {
    for (int i = 7; i >= 0; --i) {
      bool value = (c >> i) & 0x1;
      m(k / size, k % size) = static_cast<T>(value);
      k++;
    }
  }
}

template <typename T>
void EncodeImageData8Bit(const SC2APIProtocol::ImageData& data,
                         const std::function<int(int)>& transform,
                         dm_env_rpc::v1::Tensor* output) {
  int k = 0;
  int size = data.size().y();
  CHECK_GT(size, 0);
  MutableMatrix<T> m(output);
  CHECK_EQ(m.height(), data.size().x());
  CHECK_EQ(m.width(), data.size().y());
  CHECK_EQ(data.data().size(), data.size().x() * data.size().y());
  if (transform) {
    for (char c : data.data()) {
      m(k / size, k % size) = static_cast<T>(transform(c));
      k++;
    }
  } else {
    for (char c : data.data()) {
      m(k / size, k % size) = static_cast<T>(c);
      k++;
    }
  }
}

template <typename T>
void EncodeImageData32Bit(const SC2APIProtocol::ImageData& data,
                          const std::function<int(int)>& transform,
                          dm_env_rpc::v1::Tensor* output) {
  int k = 0;
  int size = data.size().y();
  CHECK_GT(size, 0);
  MutableMatrix<T> m(output);
  CHECK_EQ(m.height(), data.size().x());
  CHECK_EQ(m.width(), data.size().y());
  const auto& bytes = data.data();
  CHECK_EQ(bytes.size(), 4 * data.size().x() * data.size().y());
  if (transform) {
    for (int i = 0; i < bytes.size(); i += 4) {
      uint32_t value = *reinterpret_cast<const uint32_t*>(&bytes[i]);
      m(k / size, k % size) = static_cast<T>(transform(value));
      k++;
    }
  } else {
    for (int i = 0; i < bytes.size(); i += 4) {
      m(k / size, k % size) = *reinterpret_cast<const T*>(&bytes[i]);
      k++;
    }
  }
}

template <typename T = uint8_t>
void EncodeImageData(const SC2APIProtocol::ImageData& image,
                     const std::function<int(int)>& transform,
                     dm_env_rpc::v1::Tensor* output) {
  if (image.bits_per_pixel() == 1) {
    CHECK(transform == nullptr) << "Transform not supported for 1 bit data";
    EncodeImageData1Bit<T>(image, output);
  } else if (image.bits_per_pixel() == 8) {
    EncodeImageData8Bit<T>(image, transform, output);
  } else if (image.bits_per_pixel() == 32) {
    EncodeImageData32Bit<T>(image, transform, output);
  } else if (image.bits_per_pixel() == 0) {
    CHECK(transform == nullptr) << "Transform not supported for 0 bit data";
  } else {
    LOG(FATAL) << "EncodeImageData cannot handle bits_per_pixel="
               << image.bits_per_pixel();
  }
}

}  // namespace pysc2

#endif  // PYSC2_ENV_CONVERTER_CC_ENCODE_IMAGE_DATA_H_
