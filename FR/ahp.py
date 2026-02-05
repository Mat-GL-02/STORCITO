"""
Analytic Hierarchy Process (AHP) implementation for multi-criteria decision making.

The AHP method helps decision makers choose the best option among alternatives
by comparing them pairwise against a set of criteria.
"""

import numpy as np
from numpy.typing import NDArray


# Random Index values for consistency checking (Saaty, 1980)
# Extended table for matrices up to size 15
RANDOM_INDEX: dict[int, float] = {
    1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12,
    6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45
}

# Consistency threshold (typically 0.10)
CR_THRESHOLD: float = 0.10


def normalize_matrix(matrix: NDArray[np.floating]) -> NDArray[np.floating]:
    """
    Normalizes a pairwise comparison matrix by dividing each element
    by its column sum.

    Args:
        matrix: Square pairwise comparison matrix.

    Returns:
        Normalized matrix where each column sums to 1.

    Raises:
        ValueError: If matrix contains zero columns.
    """
    column_sums = matrix.sum(axis=0)

    if np.any(column_sums == 0):
        raise ValueError("Matrix contains columns with zero sum")

    return matrix / column_sums


def calculate_weights(normalized_matrix: NDArray[np.floating]) -> NDArray[np.floating]:
    """
    Calculates priority weights from a normalized comparison matrix.

    Args:
        normalized_matrix: Normalized pairwise comparison matrix.

    Returns:
        Array of priority weights (eigenvector approximation).
    """
    return normalized_matrix.mean(axis=1)


def consistency_ratio(
    matrix: NDArray[np.floating],
    weights: NDArray[np.floating]
) -> float:
    """
    Calculates the Consistency Ratio (CR) to verify judgment consistency.

    A CR < 0.10 is generally considered acceptable. Higher values indicate
    inconsistent judgments that should be revised.

    Args:
        matrix: Original pairwise comparison matrix.
        weights: Priority weights calculated from the matrix.

    Returns:
        Consistency Ratio (CR) value.
    """
    n = matrix.shape[0]

    if n <= 2:
        return 0.0

    # Calculate principal eigenvalue (λ_max)
    weighted_sum = matrix @ weights
    lambda_max = np.mean(weighted_sum / weights)

    # Consistency Index (CI)
    ci = (lambda_max - n) / (n - 1)

    # Random Index (RI) for matrix size
    ri = RANDOM_INDEX.get(n, 1.45)  # Default to RI for n=9 if size exceeds table

    # Consistency Ratio (CR)
    return float(ci / ri) if ri != 0 else 0.0


def is_consistent(matrix: NDArray[np.floating], threshold: float = CR_THRESHOLD) -> bool:
    """
    Checks if a pairwise comparison matrix has acceptable consistency.

    Args:
        matrix: Pairwise comparison matrix.
        threshold: Maximum acceptable CR value (default: 0.10).

    Returns:
        True if matrix is consistent, False otherwise.
    """
    normalized = normalize_matrix(matrix)
    weights = calculate_weights(normalized)
    cr = consistency_ratio(matrix, weights)
    return cr < threshold


def ahp_weights(
    matrix: NDArray[np.floating],
    check_consistency: bool = True
) -> tuple[NDArray[np.floating], float]:
    """
    Performs complete AHP analysis on a pairwise comparison matrix.

    Args:
        matrix: Square pairwise comparison matrix where element (i,j)
                represents the relative importance of criterion i over j.
                Use Saaty's 1-9 scale.
        check_consistency: If True, raises error for inconsistent matrices.

    Returns:
        Tuple of (priority weights array, consistency ratio).

    Raises:
        ValueError: If matrix is not square or if inconsistent and check enabled.

    Example:
        >>> matrix = np.array([
        ...     [1, 3, 5],
        ...     [1/3, 1, 3],
        ...     [1/5, 1/3, 1]
        ... ])
        >>> weights, cr = ahp_weights(matrix)
        >>> print(f"Weights: {weights}, CR: {cr:.4f}")
    """
    matrix = np.asarray(matrix, dtype=np.float64)

    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("Matrix must be square")

    normalized = normalize_matrix(matrix)
    weights = calculate_weights(normalized)
    cr = consistency_ratio(matrix, weights)

    if check_consistency and cr >= CR_THRESHOLD:
        raise ValueError(
            f"Inconsistent matrix (CR={cr:.4f} >= {CR_THRESHOLD}). "
            "Review pairwise comparisons."
        )

    return weights, cr


def create_comparison_matrix(comparisons: dict[tuple[int, int], float], size: int) -> NDArray[np.floating]:
    """
    Creates a pairwise comparison matrix from a dictionary of comparisons.

    Args:
        comparisons: Dictionary with (i, j) tuples as keys and comparison
                     values as values. Only upper triangle needed.
        size: Size of the square matrix.

    Returns:
        Complete pairwise comparison matrix with reciprocals filled in.

    Example:
        >>> comparisons = {(0, 1): 3, (0, 2): 5, (1, 2): 2}
        >>> matrix = create_comparison_matrix(comparisons, 3)
    """
    matrix = np.ones((size, size), dtype=np.float64)

    for (i, j), value in comparisons.items():
        matrix[i, j] = value
        matrix[j, i] = 1.0 / value

    return matrix
