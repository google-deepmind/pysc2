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

#ifndef PYSC2_ENV_CONVERTER_CC_TENSOR_UTIL_H_
#define PYSC2_ENV_CONVERTER_CC_TENSOR_UTIL_H_

#include <vector>

#include "glog/logging.h"
#include "google/protobuf/repeated_field.h"
#include "absl/strings/string_view.h"
#include "dm_env_rpc/v1/dm_env_rpc.pb.h"

namespace pysc2 {

dm_env_rpc::v1::TensorSpec TensorSpec(absl::string_view name,
                                      dm_env_rpc::v1::DataType dtype,
                                      const std::vector<int>& shape, int min,
                                      int max);

dm_env_rpc::v1::TensorSpec TensorSpec(absl::string_view name,
                                      dm_env_rpc::v1::DataType dtype,
                                      const std::vector<int>& shape);

dm_env_rpc::v1::TensorSpec Int32TensorSpec(absl::string_view name,
                                           const std::vector<int>& shape);

dm_env_rpc::v1::TensorSpec Int32ScalarSpec(absl::string_view name,
                                           int num_elements);

dm_env_rpc::v1::TensorSpec Int32ScalarSpec(absl::string_view name);

int ToScalar(const dm_env_rpc::v1::Tensor& tensor);

std::vector<int> ToVector(const dm_env_rpc::v1::Tensor& tensor);

dm_env_rpc::v1::Tensor MakeTensor(int value);

dm_env_rpc::v1::Tensor MakeTensor(const std::vector<int>& values);

template <typename T>
dm_env_rpc::v1::Tensor ZeroVector(int size);
template <typename T>
dm_env_rpc::v1::Tensor ZeroMatrix(int y, int x);

template <typename T>
void CheckTensor(const dm_env_rpc::v1::Tensor& tensor);

template <typename T>
class MutableVector {
 public:
  explicit MutableVector(dm_env_rpc::v1::Tensor* tensor) : tensor_(tensor) {
    CHECK_EQ(tensor_->shape_size(), 1);
    CheckTensor<T>(*tensor_);
  }

  T& operator()(int i) {
    CHECK_LT(i, size());
    return value(i);
  }

  int size() const { return tensor_->shape(0); }

 private:
  dm_env_rpc::v1::Tensor* tensor_;
  T& value(int index);
};

template <typename T>
class Matrix {
 public:
  explicit Matrix(const dm_env_rpc::v1::Tensor& tensor) : tensor_(tensor) {
    CHECK_EQ(tensor_.shape_size(), 2);
    CheckTensor<T>(tensor_);
  }

  T operator()(int j, int i) {
    CHECK_LT(j, height());
    CHECK_LT(i, width());
    return value(j * width() + i);
  }

  int height() const { return tensor_.shape(0); }
  int width() const { return tensor_.shape(1); }

 private:
  const dm_env_rpc::v1::Tensor& tensor_;
  T value(int index);
};

template <typename T>
class MutableMatrix {
 public:
  explicit MutableMatrix(dm_env_rpc::v1::Tensor* tensor) : tensor_(tensor) {
    CHECK_EQ(tensor_->shape_size(), 2);
    CheckTensor<T>(*tensor_);
  }

  T& operator()(int j, int i) {
    CHECK_LT(j, height());
    CHECK_LT(i, width());
    return value(j * width() + i);
  }

  int height() const { return tensor_->shape(0); }
  int width() const { return tensor_->shape(1); }

 private:
  dm_env_rpc::v1::Tensor* tensor_;
  T& value(int index);
};

}  // namespace pysc2

#endif  // PYSC2_ENV_CONVERTER_CC_TENSOR_UTIL_H_
