
def matrix_multiplication(A, B):
   
    if len(A[0]) != len(B):
        raise ValueError("Number of columns in A must equal number of rows in B")

    
    num_rows_A = len(A)
    num_cols_B = len(B[0])

    
    result = [[sum(A[i][k] * B[k][j] for k in range(len(B))) for j in range(num_cols_B)] for i in range(num_rows_A)]

    return result


if __name__ == "__main__":
    
    A = [[1, 2, 3],
         [4, 5, 6]]

    B = [[7, 8],
         [9, 10],
         [11, 12]]

   
    print(matrix_multiplication(A, B))
