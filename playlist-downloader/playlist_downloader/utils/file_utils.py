from pathlib import Path

import typer

def resolve_file(file: str, description: str = "Playlist file") -> Path: 
    file_path = Path(file)
    if not file_path.is_file() or not file_path.exists():
        raise typer.BadParameter(f"{description} '{file_path}' was not found.")
    return file_path


def resolve_folder(folder: str, description: str = "Playlist folder") -> Path: 
    folder_path = Path(folder)
    if not folder_path.is_dir() or not folder_path.exists():
        raise typer.BadParameter(f"{description} '{folder_path}' was not found.")
    return folder_path
