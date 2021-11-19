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

#ifndef PYSC2_ENV_CONVERTER_CC_CASTOPS_H_
#define PYSC2_ENV_CONVERTER_CC_CASTOPS_H_

#include <cmath>
#include <limits>
#include <type_traits>

namespace pysc2 {

// Emulating X86-64's behavior of casting long double, double or float to
// int32. Comparing to SaturatingFloatToInt<FloatType, int32>, when the
// truncated form of value is out of the representable range of int32 or NaN,
// X86-64 always returns INT32_MIN.
template <typename FloatType>
int32_t ToInt32(FloatType value);

// Return true if the truncated form of value is smaller than or equal to the
// MAX value of IntType. When the MAX value of IntType can not be represented
// precisely in FloatType, the comparison is tricky, because the MAX value of
// IntType is promoted to a FloatType value that is actually greater than what
// IntType can handle. Also note that when value is nan, this function will
// return false.
template <typename FloatType, typename IntType>
bool SmallerThanOrEqualToIntMax(FloatType value) {
  if (value <= 0) {
    return true;
  }
  if (std::isnan(value) || std::isinf(value)) {
    return false;
  }
  // Set exp such that value == f * 2^exp for some f with |f| in [0.5, 1.0),
  // unless value is zero in which case exp == 0. Note that this implies that
  // the magnitude of value is strictly less than 2^exp.
  int exp = 0;
  std::frexp(value, &exp);

  // Let N be the number of non-sign bits in the representation of IntType.
  // If the magnitude of value is strictly less than 2^N, the truncated version
  // of value is representable as IntType.
  static_assert(std::numeric_limits<FloatType>::radix == 2,
                "return type size must be based on 2");
  return exp <= std::numeric_limits<IntType>::digits;
}

template <typename FloatType>
int32_t ToInt32(FloatType value) {
  static_assert(std::is_floating_point<FloatType>::value,
                "value must have floating point type");
  // For values between (INT32_MIN-1, INT32_MIN), fall to the else case.
  if ((value >= std::numeric_limits<int32_t>::min()) &&
      SmallerThanOrEqualToIntMax<FloatType, int32_t>(value)) {
    return static_cast<int32_t>(value);
  } else {
    // For out-of-bound value, including NaN, x86_64 returns INT32_MIN.
    return std::numeric_limits<int32_t>::min();
  }
}

}  // namespace pysc2

#endif  // PYSC2_ENV_CONVERTER_CC_CASTOPS_H_
