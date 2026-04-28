"""
Step Dependencies and Parameters Configuration
Based on the original qmodel project specification
"""
import importlib
# importing sslh-cli
sslh = importlib.import_module("sslh-cli")

# Defines the dependency structure for each step function
# Each step maps to a list of required dependency slots
# Each slot can be satisfied by one of multiple acceptable function types
STEP_DEPENDENCIES = sslh.__sanitizer.STEP_DEPENDENCIES

# Defines the parameter schema for each step function
# (Used for validation - not needed for job creation)
STEP_PARAMETERS = sslh.__sanitizer.STEP_PARAMETERS

def get_step_dependencies(function_name: str) -> list:
    """
    Get the list of dependencies for a given step function.

    Args:
        function_name: Name of the step function (e.g., 'preprocessing', 'sorting')

    Returns:
        List of dependency slots, each slot can be satisfied by one of multiple functions

    Example:
        get_step_dependencies('analyzer')
        → [
            ('recording', 'combined_recording', 'preprocessing', 'load_preprocessing'),
            ('sorting', 'load_sorting', 'import_from_phy')
          ]
    """
    return STEP_DEPENDENCIES.get(function_name, [])


def validate_dependencies(
    function_name: str, depends_on: list, available_functions: dict
) -> tuple:
    """
    Validate that the provided dependencies satisfy the requirements for a function.

    Args:
        function_name: Name of the step function
        depends_on: List of function names this step depends on
        available_functions: Dict mapping function names to their identifiers (hashes)

    Returns:
        (is_valid: bool, error_message: str or None)
    """
    required_deps = get_step_dependencies(function_name)

    # If no dependencies required, return True
    if not required_deps:
        if depends_on:
            return False, f"{function_name} should not have dependencies"
        return True, None

    # Check correct number of dependency slots
    if len(depends_on) != len(required_deps):
        return (
            False,
            f"{function_name} requires {len(required_deps)} dependencies, got {len(depends_on)}",
        )

    # Check each dependency satisfies its slot
    for slot_idx, (dep_func, required_funcs) in enumerate(
        zip(depends_on, required_deps)
    ):
        if dep_func not in available_functions:
            return False, f"Dependency {dep_func} not found in available functions"

        # Check if the dependency function type matches one of the acceptable types for this slot
        dep_func_type = available_functions[dep_func]["function"]
        if isinstance(required_funcs, tuple):
            if dep_func_type not in required_funcs:
                return (
                    False,
                    f"Slot {slot_idx + 1} of {function_name} requires one of {required_funcs}, got {dep_func_type}",
                )
        else:
            if dep_func_type != required_funcs:
                return (
                    False,
                    f"Slot {slot_idx + 1} of {function_name} requires {required_funcs}, got {dep_func_type}",
                )

    return True, None
