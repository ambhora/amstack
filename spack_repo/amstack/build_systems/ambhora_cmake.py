# SPDX-License-Identifier: Apache-2.0

from spack_repo.builtin.build_systems.cmake import CMakePackage


class AmbhoraCMakePackage(CMakePackage):
    """Common build policy for BESA-generated Ambhora CMake projects."""

    # Maps Spack boolean variant names to BESA PROJECT_FEATURES names.
    besa_feature_variants = {}

    def cmake_args(self):
        feature_overrides = []
        for variant, feature in self.besa_feature_variants.items():
            enabled = bool(self.spec.variants[variant].value)
            feature_overrides.append(feature if enabled else f"~{feature}")

        return [self.define("PROJECT_FEATURES", ";".join(feature_overrides))]
