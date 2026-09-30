from sklearn.preprocessing import StandardScaler
from app.data.loader import iter_csv_chunks


def count_cleaned_rows(file_paths, feature_cols, label_col=None, timestamp_col=None, chunksize=200_000):
    """Counts rows after the SAME cleaning pass fit_scaler_streaming/build_states_for_file
    use (dtype coercion, inf->nan, dropna), across file_paths in the given
    (assumed chronological) order. A chronological train/val row cutoff
    computed from this lines up exactly with what those functions will
    actually stream, so the cutoff used to restrict scaler fitting is not an
    approximation based on raw, uncleaned line counts.

    Returns (total_rows, per_file_row_counts).
    """
    total = 0
    per_file = []
    for path in file_paths:
        file_total = 0
        for chunk in iter_csv_chunks(path, feature_cols, label_col, timestamp_col, chunksize):
            file_total += len(chunk)
        per_file.append(file_total)
        total += file_total
    return total, per_file


def fit_scaler_streaming(file_paths, feature_cols, label_col=None, timestamp_col=None,
                          chunksize=200_000, row_cutoff=None):
    """Fits the scaler on cleaned rows in chronological order across
    file_paths, in the order given.

    row_cutoff (optional): if given, ONLY the first `row_cutoff` cleaned
    rows (chronologically, across all files) are used to fit the scaler --
    rows at/after the cutoff (the validation/test split) are streamed
    through but never passed to partial_fit. This is how scaler fitting
    avoids training-data leakage: the same chronological cutoff used to
    split sequences into train/val below is applied here too, so no
    validation/test row is ever allowed to influence the scaler. Pass
    row_cutoff=None only when file_paths has already been restricted to
    training data some other way.
    """
    scaler = StandardScaler()
    total_rows = 0
    fitted_rows = 0
    for path in file_paths:
        for chunk in iter_csv_chunks(path, feature_cols, label_col, timestamp_col, chunksize):
            chunk_len = len(chunk)
            if row_cutoff is None:
                scaler.partial_fit(chunk[feature_cols].values)
                fitted_rows += chunk_len
            elif total_rows < row_cutoff:
                remaining = row_cutoff - total_rows
                if remaining >= chunk_len:
                    scaler.partial_fit(chunk[feature_cols].values)
                    fitted_rows += chunk_len
                else:
                    scaler.partial_fit(chunk[feature_cols].values[:remaining])
                    fitted_rows += remaining
            total_rows += chunk_len

    suffix = " (chronological train-only split -- no val/test leakage)" if row_cutoff is not None else ""
    print(f"[scaler] fitted on {fitted_rows} row(s) out of {total_rows} total across "
          f"{len(file_paths)} file(s){suffix}")
    return scaler
