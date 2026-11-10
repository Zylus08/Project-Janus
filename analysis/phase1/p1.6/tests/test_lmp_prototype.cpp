#include <iostream>
#include <cstdint>
#include <vector>
#include <chrono>

int main() {
    std::cout << "LMP Prototype Test Harness" << std::endl;
    for (int d = 1; d <= 4; ++d) {
        int l1 = 3 + 3 * d * d;
        int l2 = 3 + 2 * d * d;
        std::cout << "Depth " << d << ": L1 threshold = " << l1 << ", L2 threshold = " << l2 << std::endl;
    }
    return 0;
}

