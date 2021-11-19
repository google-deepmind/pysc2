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

#include "pysc2/env/converter/cc/tensor_util.h"

#include <cstdint>
#include <vector>

#include "glog/logging.h"
#include "google/protobuf/repeated_field.h"
#include "absl/strings/string_view.h"
#include "dm_env_rpc/v1/dm_env_rpc.pb.h"

namespace pysc2 {

dm_env_rpc::v1::TensorSpec TensorSpec(absl::string_view name,
                                      dm_env_rpc::v1::DataType dtype,
                                      const std::vector<int>& shape, int min,
                                      int max) {
  dm_env_rpc::v1::TensorSpec spec = TensorSpec(name, dtype, shape);
  switch (dtype) {
    case dm_env_rpc::v1::INT32:
      spec.mutable_min()->mutable_int32s()->add_array(min);
      spec.mutable_max()->mutable_int32s()->add_array(max);
      break;
    case dm_env_rpc::v1::UINT8:
      spec.mutable_min()->mutable_uint8s()->mutable_array()->push_back(min);
      spec.mutable_max()->mutable_uint8s()->mutable_array()->push_back(max);
      break;
    default:
      CHECK(false) << "Unhandled dtype: " << dtype;
  }
  return spec;
}

dm_env_rpc::v1::TensorSpec TensorSpec(absl::string_view name,
                                      dm_env_rpc::v1::DataType dtype,
                                      const std::vector<int>& shape) {
  dm_env_rpc::v1::TensorSpec spec;
  spec.set_name(std::string(name));
  spec.set_dtype(dtype);
  for (auto s : shape) {
    spec.add_shape(s);
  }
  return spec;
}

dm_env_rpc::v1::TensorSpec Int32TensorSpec(absl::string_view name,
                                           const std::vector<int>& shape) {
  return TensorSpec(name, dm_env_rpc::v1::DataType::INT32, shape);
}

dm_env_rpc::v1::TensorSpec Int32ScalarSpec(absl::string_view name,
                                           int num_elements) {
  return TensorSpec(name, dm_env_rpc::v1::DataType::INT32, {}, 0,
                    num_elements - 1);
}

dm_env_rpc::v1::TensorSpec Int32ScalarSpec(absl::string_view name) {
  dm_env_rpc::v1::TensorSpec spec;
  spec.set_name(std::string(name));
  spec.set_dtype(dm_env_rpc::v1::DataType::INT32);
  return spec;
}

int ToScalar(const dm_env_rpc::v1::Tensor& tensor) {
  // Though we ask for int32s, Python -> C++ over pybind turns integers
  // into int64; so for convenience, permit that.
  switch (tensor.payload_case()) {
    case dm_env_rpc::v1::Tensor::kInt32S:
      CHECK_EQ(tensor.int32s().array_size(), 1);
      return tensor.int32s().array(0);
    case dm_env_rpc::v1::Tensor::kInt64S:
      CHECK_EQ(tensor.int64s().array_size(), 1);
      return tensor.int64s().array(0);
    default:
      CHECK(false) << "Unhandled payload case when parsing scalar tensor: "
                   << tensor.payload_case();
  }
}

std::vector<int> ToVector(const dm_env_rpc::v1::Tensor& tensor) {
  // Though we ask for int32s, Python -> C++ over pybind turns integers
  // into int64; so for convenience, permit that.
  std::vector<int> result;
  switch (tensor.payload_case()) {
    case dm_env_rpc::v1::Tensor::kInt32S:
      result.reserve(tensor.int32s().array_size());
      for (int i = 0; i < tensor.int32s().array_size(); ++i) {
        result.push_back(tensor.int32s().array(i));
      }
      break;
    case dm_env_rpc::v1::Tensor::kInt64S:
      result.reserve(tensor.int64s().array_size());
      for (int i = 0; i < tensor.int64s().array_size(); ++i) {
        result.push_back(tensor.int64s().array(i));
      }
      break;
    default:
      CHECK(false) << "Unhandled payload case when parsing vector tensor: "
                   << tensor.payload_case();
  }
  return result;
}

dm_env_rpc::v1::Tensor MakeTensor(int value) {
  dm_env_rpc::v1::Tensor tensor;
  tensor.mutable_int32s()->add_array(value);
  return tensor;
}

dm_env_rpc::v1::Tensor MakeTensor(const std::vector<int>& values) {
  dm_env_rpc::v1::Tensor tensor;
  tensor.add_shape(values.size());
  for (auto v : values) {
    tensor.mutable_int32s()->add_array(v);
  }
  return tensor;
}

template <>
dm_env_rpc::v1::Tensor ZeroVector<int32_t>(int size) {
  dm_env_rpc::v1::Tensor tensor;
  tensor.add_shape(size);
  for (int i = 0; i < size; ++i) {
    tensor.mutable_int32s()->add_array(0);
  }
  return tensor;
}

template <>
dm_env_rpc::v1::Tensor ZeroMatrix<int32_t>(int y, int x) {
  dm_env_rpc::v1::Tensor tensor;
  tensor.add_shape(y);
  tensor.add_shape(x);
  for (int i = 0; i < y * x; ++i) {
    tensor.mutable_int32s()->add_array(0);
  }
  return tensor;
}

template <>
dm_env_rpc::v1::Tensor ZeroMatrix<int64_t>(int y, int x) {
  dm_env_rpc::v1::Tensor tensor;
  tensor.add_shape(y);
  tensor.add_shape(x);
  for (int i = 0; i < y * x; ++i) {
    tensor.mutable_int64s()->add_array(0);
  }
  return tensor;
}

template <>
dm_env_rpc::v1::Tensor ZeroMatrix<uint8_t>(int y, int x) {
  dm_env_rpc::v1::Tensor tensor;
  tensor.add_shape(y);
  tensor.add_shape(x);
  *tensor.mutable_uint8s()->mutable_array() =
      std::string(y * x, static_cast<char>(0));
  return tensor;
}

int GetNumElements(const google::protobuf::RepeatedField<int32_t>& tensor_shape) {
  int num_elements = 1;
  for (auto s : tensor_shape) {
    num_elements *= s;
  }
  return num_elements;
}

template <>
void CheckTensor<int32_t>(const dm_env_rpc::v1::Tensor& tensor) {
  CHECK_EQ(GetNumElements(tensor.shape()), tensor.int32s().array_size());
}

template <>
void CheckTensor<int64_t>(const dm_env_rpc::v1::Tensor& tensor) {
  CHECK_EQ(GetNumElements(tensor.shape()), tensor.int64s().array_size());
}

template <>
void CheckTensor<uint8_t>(const dm_env_rpc::v1::Tensor& tensor) {
  CHECK_EQ(GetNumElements(tensor.shape()), tensor.uint8s().array().size());
}

template <>
int32_t& MutableVector<int32_t>::value(int index) {
  return *tensor_->mutable_int32s()->mutable_array()->Mutable(index);
}

template <>
int32_t Matrix<int32_t>::value(int index) {
  return tensor_.int32s().array(index);
}

template <>
int64_t Matrix<int64_t>::value(int index) {
  return tensor_.int64s().array(index);
}

template <>
uint8_t Matrix<uint8_t>::value(int index) {
  const std::string& string = tensor_.uint8s().array();
  const uint8_t* array = reinterpret_cast<const uint8_t*>(string.data());
  return array[index];
}

template <>
int32_t& MutableMatrix<int32_t>::value(int index) {
  return *tensor_->mutable_int32s()->mutable_array()->Mutable(index);
}

template <>
int64_t& MutableMatrix<int64_t>::value(int index) {
  return *tensor_->mutable_int64s()->mutable_array()->Mutable(index);
}

template <>
uint8_t& MutableMatrix<uint8_t>::value(int index) {
  std::string* string = tensor_->mutable_uint8s()->mutable_array();
  uint8_t* array = reinterpret_cast<uint8_t*>(string->data());
  return array[index];
}

}  // namespace pysc2
