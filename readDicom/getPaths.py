import json
import shutil
import os


def copyInputDirToOutputDir(source_dir, dest_dir):
    """
    Copies files and subdirectories recursively from source_dir to dest_dir.

    Args:
        source_dir: Path to the source directory.
        dest_dir: Path to the destination directory.  Will be created if it doesn't exist.

    Raises:
        shutil.Error: If there's an error during the copy operation (e.g., file already exists).
        OSError: if the source directory does not exist.
    """
    if not os.path.exists(source_dir):
        raise OSError(f"Source directory '{source_dir}' does not exist.")
    try:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)
        print(f"Start transfer files from '{source_dir}' to '{dest_dir}'")
        shutil.copytree(source_dir, dest_dir)
        print(f"Files transferred successfully from '{source_dir}' to '{dest_dir}'")
    except shutil.Error as e:
        print(f"Error copying files: {e}")
        raise  # Re-raise the exception to handle it appropriately in your application.
    except OSError as e:
        print(f"OS error during file copy: {e}")
        raise  # Re-raise the exception to handle it appropriately in your application.


