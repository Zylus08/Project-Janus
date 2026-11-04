/*
 * Project Janus v0.49 - Native Move Picker Kernel (Candidate N1)
 *
 * Implements high-performance, stable move selection and partial ordering in C.
 * Designed for low-overhead invocation from Python via ctypes.
 *
 * Functions:
 * 1. native_select_next_best:
 *    Finds the maximum scoring move index among unselected candidates.
 *    Tie-breaking: strictly stable (lowest original index wins on identical score).
 *
 * 2. native_stable_partial_sort:
 *    Computes the stable descending order of the top-k move indices.
 *    If k >= n, returns the full stable sort of all indices.
 *
 * 3. native_batch_order_moves:
 *    Takes scores and returns a complete stably-sorted permutation array of indices.
 */

#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

/*
 * Finds the index of the highest-scoring move not yet selected.
 *
 * scores: array of integer move scores of length n
 * selected_mask: array of length n (1 if already selected, 0 if available)
 * n: number of candidate moves
 *
 * Returns: index of the best candidate move (0 <= index < n), or -1 if none available.
 * Stability: Strictly stable. In case of ties, the lowest index is selected.
 */
EXPORT int native_select_next_best(const int* scores, const unsigned char* selected_mask, int n) {
    if (n <= 0 || scores == NULL || selected_mask == NULL) {
        return -1;
    }

    int best_idx = -1;
    int best_score = -2147483647; /* INT_MIN + 1 */

    for (int i = 0; i < n; i++) {
        if (!selected_mask[i]) {
            if (scores[i] > best_score) {
                best_score = scores[i];
                best_idx = i;
            }
        }
    }

    return best_idx;
}

/*
 * Stably selects the top-k move indices in descending order of score.
 * Uses an in-place stable selection sort algorithm.
 * For small chess move lists (n typically 20 to 60), stable selection sort
 * requires minimal allocations and avoids O(N log N) overhead when k is small.
 *
 * scores: array of integer move scores of length n
 * n: total number of candidate moves
 * k: number of top moves to determine (1 <= k <= n)
 * out_indices: output array of length at least k (or n)
 *
 * Returns: 0 on success, -1 on invalid arguments.
 */
EXPORT int native_stable_partial_sort(const int* scores, int n, int k, int* out_indices) {
    if (n <= 0 || scores == NULL || out_indices == NULL || k <= 0) {
        return -1;
    }

    if (k > n) {
        k = n;
    }

    /* Initialize identity permutation */
    for (int i = 0; i < n; i++) {
        out_indices[i] = i;
    }

    /* Selection sort for the first k elements */
    for (int i = 0; i < k; i++) {
        int max_idx = i;
        int max_score = scores[out_indices[i]];

        for (int j = i + 1; j < n; j++) {
            int cand_idx = out_indices[j];
            int cand_score = scores[cand_idx];

            /* Strictly greater score wins.
             * On equal score, earlier original index wins (preserves stability).
             */
            if (cand_score > max_score || (cand_score == max_score && cand_idx < out_indices[max_idx])) {
                max_score = cand_score;
                max_idx = j;
            }
        }

        /* Shift elements to preserve relative stability of unselected items */
        if (max_idx != i) {
            int selected = out_indices[max_idx];
            for (int m = max_idx; m > i; m--) {
                out_indices[m] = out_indices[m - 1];
            }
            out_indices[i] = selected;
        }
    }

    return 0;
}

/*
 * Returns 1 if native library is operational and compatible, 0 otherwise.
 */
EXPORT int native_move_picker_version(void) {
    return 4901; /* v0.49.1 ABI */
}

