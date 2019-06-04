import numpy as np
import poly_brute_force as poly


def quadratize(extended_qubo):
    # quadratizes up to 4-body interactions
    # reduction by substitution (Rosenberg 1975)
    # quadratization in discrete optimization and quantum mechanics
    # section V. A.
    # Nike Dattani arXiv: 1901.04405
    num_problem_qubits = len(extended_qubo['qubit_residual_dim1'])
    num_auxiliary_qubits = int(num_problem_qubits * (num_problem_qubits - 1) / 2)
    num_qubo_qubits = num_problem_qubits + num_auxiliary_qubits
    qubo = np.zeros((num_qubo_qubits, num_qubo_qubits), float)

    # construct constraint equations
    # auxiliary qubit a_ij = b_i b_j is enforced by
    # b_i b_j - 2 b_i a_ij - 2 b_j a_ij + 3 a_ij
    coeff_scale = 0
    coeff_bb = coeff_scale * 1
    coeff_ba = coeff_scale * -2
    coeff_aa = coeff_scale * 3

    if coeff_bb + 2. * coeff_ba + coeff_aa == 0:
        pass
    else:
        print("constraint equation poorly defined")
        import sys
        sys.exit()

    # constrain b_i b_j
    for index_j in range(num_problem_qubits):
        for index_i in range(index_j):
            qubo[index_i, index_j] = coeff_bb

    # constrain -2 b_i a_ij -2 b_j a_ij
    qubo_to_aux_index = dict()  # maps auxiliary qubit indices (i,j) to qubo matrix index
    accumulate = 0
    row_counter = 0
    triangle_counter = num_problem_qubits - 1
    for index_j in range(num_problem_qubits, num_qubo_qubits):
        qubo[row_counter, index_j] = coeff_ba
        accumulate += 1
        qubo_to_aux_index[(row_counter, accumulate + row_counter)] = index_j
        if accumulate == triangle_counter:
            accumulate = 0
            row_counter += 1
            triangle_counter -= 1
    accumulate = 0
    row_counter = 1
    triangle_counter = num_problem_qubits - 1
    for index_row in range(num_problem_qubits):
        for index_ij in range(triangle_counter):
            index_i = row_counter + index_ij
            index_j = num_problem_qubits + index_ij + accumulate
            qubo[index_i, index_j] = coeff_ba
        accumulate += index_ij + 1
        row_counter += 1
        triangle_counter -= 1

    # constrain 3 a_ij
    for index_ij in range(num_problem_qubits, num_qubo_qubits):
        qubo[index_ij, index_ij] = coeff_aa

    import pandas as pd
    print(pd.DataFrame(qubo))

    # load extended_qubo into quadratized qubo
    # dim 0
    qubo_constant = extended_qubo['qubit_residual_dim0']

    # dim 1, dim 2 diagonal, dim 3 3 repeating indices, dim 4 4 repeating indices
    for index_ij in range(num_problem_qubits):
        qubo[index_ij, index_ij] += extended_qubo['qubit_residual_dim1'][index_ij]
        qubo[index_ij, index_ij] += extended_qubo['qubit_residual_dim2'][index_ij, index_ij]
        qubo[index_ij, index_ij] += extended_qubo['qubit_residual_dim3'][index_ij, index_ij, index_ij]
        qubo[index_ij, index_ij] += extended_qubo['qubit_residual_dim4'][index_ij, index_ij, index_ij, index_ij]

    # dim 2 off diagonal, dim 3 2 repeating indices, dim 4 3 repeating indices
    # accumulate to upper triangular matrix
    from sympy.utilities.iterables import multiset_permutations
    for index_j in range(num_problem_qubits):
        for index_i in range(num_problem_qubits):
            if index_i == index_j:
                continue
            sorted_indices = np.sort([index_i, index_j])
            row_index = sorted_indices[0]
            col_index = sorted_indices[1]
            # dim 2
            qubo[row_index, col_index] += extended_qubo['qubit_residual_dim2'][index_i, index_j]
            # dim 3
            index_permutations = list(multiset_permutations([index_i, index_i, index_j]))
            qubo[row_index, col_index] += sum(
                [extended_qubo['qubit_residual_dim3'][idx[0], idx[1], idx[2]] for idx in index_permutations])
            # dim 4
            index_permutations = list(multiset_permutations([index_i, index_i, index_i, index_j]))
            qubo[row_index, col_index] += sum(
                [extended_qubo['qubit_residual_dim4'][idx[0], idx[1], idx[2], idx[3]] for idx in index_permutations])

    # dim 3 off diagonal, dim 4 2 repeating indices
    # accumulate to upper triangular matrix
    for index_k in range(num_problem_qubits):
        for index_j in range(num_problem_qubits):
            for index_i in range(num_problem_qubits):
                if len(np.unique([index_i, index_j, index_k])) < 3:
                    continue
                sorted_indices = np.sort([index_i, index_j, index_k])
                row_index = sorted_indices[0]
                col_index = qubo_to_aux_index[(sorted_indices[1], sorted_indices[2])]
                # dim 3
                qubo[row_index, col_index] += extended_qubo['qubit_residual_dim3'][index_i, index_j, index_k]
                # dim 4
                index_permutations = list(multiset_permutations([index_i, index_i, index_j, index_k]))
                qubo[row_index, col_index] += sum(
                    [extended_qubo['qubit_residual_dim4'][idx[0], idx[1], idx[2], idx[3]] for idx in
                     index_permutations])
    # dim 4 off diagonal
    # accumulate to upper triangular matrix
    for index_l in range(num_problem_qubits):
        for index_k in range(num_problem_qubits):
            for index_j in range(num_problem_qubits):
                for index_i in range(num_problem_qubits):
                    if len(np.unique([index_i, index_j, index_k, index_l])) < 4:
                        continue
                    sorted_indices = np.sort([index_i, index_j, index_k, index_l])
                    row_index = qubo_to_aux_index[(sorted_indices[0], sorted_indices[1])]
                    col_index = qubo_to_aux_index[(sorted_indices[2], sorted_indices[3])]
                    qubo[row_index, col_index] += extended_qubo['qubit_residual_dim4'][
                        index_i, index_j, index_k, index_l]

    print(pd.DataFrame(qubo))
    print(qubo_constant)
    return qubo, qubo_constant


def argmin_QUBO(qubo, qubo_constant):
    # this is for an actual quadratic qubo (yes yes qubo = quadratic binary blah blah...)
    num_of_qubits = len(qubo)
    ground_state_eigenvector = poly.int_to_bin(hilbert_index=0, num_of_qubits=num_of_qubits)
    ground_state_eigenvalue = np.einsum('i,ij,j', ground_state_eigenvector.T, qubo,
                                        ground_state_eigenvector) + qubo_constant
    result_eigenvalue = []
    result_eigenvector = []
    for h_idx in range(2 ** num_of_qubits):  # loop over all 2^n possibilities
        eigenvector = poly.int_to_bin(h_idx, num_of_qubits)
        eigenvalue = np.einsum('i,ij,j', eigenvector.T, qubo, eigenvector) + qubo_constant
        result_eigenvalue.append(eigenvalue)
        result_eigenvector.append(eigenvector)
        if eigenvalue < ground_state_eigenvalue:
            ground_state_eigenvalue = eigenvalue
            ground_state_eigenvector = eigenvector
    return ground_state_eigenvector, result_eigenvalue, result_eigenvector


def main():
    extended_qubo, accumulated_qubo, basis_map = poly.import_QUBO()
    qubo, qubo_constant = quadratize(extended_qubo)
    ground_state_eigenvector, result_eigenvalue, result_eigenvector = argmin_QUBO(qubo, qubo_constant)
    print(np.sort(result_eigenvalue))
    print(ground_state_eigenvector)


if __name__ == "__main__":
    main()
