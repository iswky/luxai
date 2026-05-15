import os
import subprocess
from typing import List

def convert_files_to_pdf(folder_path: str, files: List[str]):
    """
    Identifies and converts multiple files (docs and sheets) to PDF.

    @param folder_path The directory containing the files.
    @param files A list of filenames to be processed.
    """
    # checking the existence of the directory
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Directory '{folder_path}' does not exist")

    if not os.path.isdir(folder_path):
        raise NotADirectoryError(f"'{folder_path}' is not a directory")

    for filename in files:
        file_path = os.path.join(folder_path, filename)

        convert1file2pdf(file_path)

def convert1file2pdf(file_path: str):
    """
    Converts a single file to PDF.

    @param file_path The full path of the file to convert.
    """
    # checking the existence of the directory
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Directory '{file_path}' does not exist")

    file_extension = os.path.splitext(file_path)[1].lower()
    output_filename = os.path.splitext(file_path)[0] + ".pdf"

    try:
        if file_extension in ['.pdf']:
            return
        elif file_extension in ['.xlsx', '.xls']:
            convert_excel_to_pdf(file_path, output_filename)
        elif file_extension in ['.docx', '.doc']:
            convert_word_to_pdf(file_path, output_filename)
        else:
            print(f"Unsupported format: {file_path}")
            return

        print(f"Converted: {file_path} -> {output_filename}")

    except Exception as e:
        print(f"Conversion error {file_path}: {str(e)}")



def convert_to_pdf(path: str, files: List[str]):
    """
    Batch converts multiple office documents to PDF.

    @param path The directory path containing the documents.
    @param files A list of target filenames to convert.
    """

    # checking the existence of the directory
    if not os.path.exists(path):
        raise FileNotFoundError(f"Directory '{path}' does not exist")

    if not os.path.isdir(path):
        raise NotADirectoryError(f"'{path}' is not a directory")

    converted_files = []
    failed_files = []

    for filename in files:
        file_path = os.path.join(path, filename)
        # print(file_path)

        # checking the existence of the file
        if not os.path.exists(file_path):
            print(f"File not found: {filename}")
            failed_files.append(filename)
            continue

        # getting the file extension
        file_extension = os.path.splitext(filename)[1].lower()
        output_filename = os.path.splitext(filename)[0] + ".pdf"
        output_path = os.path.join(path, output_filename)

        try:
            if file_extension in ['.pdf']:
                continue
            if file_extension in ['.xlsx', '.xls']:
                convert_excel_to_pdf(file_path, output_path)
            if file_extension in ['.docx']:
                convert_word_to_pdf(file_path, output_path)
            else:
                print(f"Unsupported format: {filename}")
                failed_files.append(filename)
                continue

            print(f"Converted: {filename} -> {output_filename}")
            converted_files.append(filename)

        except Exception as e:
            print(f"Conversion error {filename}: {str(e)}")
            failed_files.append(filename)

    # statistics output
    print("\n" + "="*50)
    print(f"Conversion stats:")
    print(f"Success: {len(converted_files)} files")
    print(f"Errors: {len(failed_files)} files")

    if failed_files:
        print(f"\n Failed to convert: {', '.join(failed_files)}")

def convert_word_to_pdf(input_path: str, output_path: str = None):
    """
    Converts a Word file to PDF using LibreOffice.

    @param input_path Source file path.
    @param output_path Destination PDF path (optional).
    @return The output path.
    """


    import subprocess

    # if output_path is not specified, create next to the source file
    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + '.pdf'

    # we get the directory for output
    output_dir = os.path.dirname(output_path)
    if not output_dir:
        output_dir = '.'

    # conversion via libreoffice
    cmd = [
        'libreoffice',
        '--headless',           # no gui
        '--convert-to', 'pdf',  # convert to pdf
        '--outdir', output_dir, # output directory
        input_path              # input file
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # libreoffice stashes a file with the same name in output_dir
        generated_pdf = os.path.join(output_dir, os.path.basename(input_path).replace('.docx', '.pdf'))

        # if you need to rename or move
        if generated_pdf != output_path:
            os.rename(generated_pdf, output_path)

        print(f"Conversion successful: {output_path}")
        return output_path

    except subprocess.CalledProcessError as e:
        print(f"Conversion error: {e}")
        print(f"Stderr: {e.stderr}")
        raise
    except FileNotFoundError:
        raise Exception("LibreOffice is not installed. Install it: sudo apt install libreoffice")

def convert_excel_to_pdf(input_path: str, output_path: str):
    """
    Converts an Excel spreadsheet to a PDF file using pandas and matplotlib.

    @param input_path Source Excel file path.
    @param output_path Destination PDF file path.
    """

    import pandas as pd
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    # print(input_path)

    # read with additional params
    df = pd.read_excel(
        input_path,
        header=None,  # don't use the first line as a title
        keep_default_na=False,  # don't replace empty values ​​with nan
        na_filter=False  # disable na filtering
    )

    # removing completely empty rows and columns
    df = df.dropna(how='all', axis=0)  # removing empty lines
    df = df.dropna(how='all', axis=1)  # removing empty columns

    print(f"Table size: {df.shape}")

    if df.empty or df.shape[0] == 0 or df.shape[1] == 0:
        raise ValueError("Excel file contains no data")

    # replace nan with empty strings
    df = df.fillna('')

    # calculate the size
    num_rows, num_cols = df.shape
    fig_width = max(12, num_cols * 2)
    fig_height = max(8, num_rows * 0.6)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis('tight')
    ax.axis('off')

    # create a table without headers (since header=none)
    table = ax.table(
        cellText=df.values,
        cellLoc='left',  # left alignment
        loc='center',
        colWidths=[1.0/num_cols] * num_cols
    )

    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)

    with PdfPages(output_path) as pdf:
        pdf.savefig(fig, bbox_inches='tight', dpi=150)

    plt.close()
    print(f"PDF saved: {output_path}")
