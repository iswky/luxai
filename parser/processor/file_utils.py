import os
from typing import List

def delete_files(path: str, filenames: List[str]):
    """
    Deletes specified files from the given directory path.

    @param path The directory path containing the files.
    @param filenames A list of specific file names to delete.
    """

    for filename in filenames:
        file_path = os.path.join(path, filename)

        file_extension = os.path.splitext(filename)[1].lower()

        if file_extension in ['.pdf']:
            continue

        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"Deleted: {filename}")
            else:
                print(f"File not found: {filename}")
        except Exception as e:
            print(f"Error deleting {filename}: {e}")

def delete_extra_files(path: str, Neccesary_files: List[str]):
    """
    Deletes all files in a directory except those explicitly marked as necessary.

    @param path The directory path to clean up.
    @param Neccesary_files A list of file names that should NOT be deleted.
    """

    # checking if the directory exists
    if not os.path.exists(path):
        raise FileNotFoundError(f"Directory '{path}' does not exist")

    # checking if the path is a directory
    if not os.path.isdir(path):
        raise NotADirectoryError(f"'{path}' is not a directory")

    # get a list of all files in a directory
    all_files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

    print(all_files)

    # we create many necessary files for quick search
    necessary_set = set(Neccesary_files)

    # removing unnecessary files
    deleted_count = 0
    for file in all_files:
        if file not in necessary_set:
            print(f"deleting {file}")
            file_path = os.path.join(path, file)
            try:
                os.remove(file_path)
                print(f"Deleted: {file}")
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting '{file}': {e}")

    print(f"\nDeleted files: {deleted_count}")
    print(f"Saved files: {len(necessary_set & set(all_files))}")

def rename_all_files_in_folder(folder_path: str, tender_id: str):
    """
    Renames all files in a folder sequentially, prefixing them with the tender ID.

    @param folder_path The directory containing the files to rename.
    @param tender_id The tender ID to use as a prefix.
    """

    if not os.path.exists(folder_path):
        print(f"Folder {folder_path} not found")
        return

    files_in_folder = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

    i = 1
    for file in files_in_folder:
        file_ext = os.path.splitext(file)[1]
        old_path = os.path.join(folder_path, file)
        new_path = os.path.join(folder_path, f"{tender_id}_{i}{file_ext}")

        os.rename(old_path, new_path)
        i += 1
