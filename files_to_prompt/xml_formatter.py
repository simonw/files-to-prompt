from typing import List, Union, Optional
import base64
import mimetypes
import os
import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils
import click


def read_file(file_path: str, base64_encode: bool = False) -> str:
    mode = "rb" if base64_encode else "r"
    with open(file_path, mode) as file:
        content = file.read()
        if base64_encode:
            return base64.b64encode(content).decode("utf-8")
        if isinstance(content, bytes):
            return content.decode("utf-8")
        return content


def create_document_xml(
    files: List[str], base64_encode_binary: bool = False
) -> ET.Element:
    root = ET.Element("documents")
    index = 0
    for file_path in files:
        full_path = os.path.abspath(file_path)
        # The goal here is to base64 encode binary files when base64_encode_binary=True,
        # but always leave plain text files as text (utf-8).
        try:
            file_content = read_file(file_path, base64_encode=False)
            is_base64 = False
        except UnicodeDecodeError:
            if base64_encode_binary:
                try:
                    file_content = read_file(file_path, base64_encode=True)
                    is_base64 = True
                except IOError as e:
                    warning_message = f"Error reading file {file_path}: {e}"
                    click.echo(click.style(warning_message, fg="red"), err=True)
                    continue
            else:
                # If base64_encode_binary is False and we can't decode as utf-8, skip the file
                warning_message = (
                    f"Warning: Skipping file {file_path} due to UnicodeDecodeError"
                )
                click.echo(click.style(warning_message, fg="red"), err=True)
                continue
        except IOError as e:
            warning_message = f"Error reading file {file_path}: {e}"
            click.echo(click.style(warning_message, fg="red"), err=True)
            continue

        document = ET.SubElement(root, "document", index=str(index))
        source = ET.SubElement(document, "source")
        source.text = file_path

        document_content = ET.SubElement(document, "document_content")

        if not is_base64:
            file_content = saxutils.escape(file_content)

        document_content.text = file_content
        index += 1

    return root


def write_document_xml(xml_element: ET.Element) -> str:
    return ET.tostring(xml_element, encoding="unicode", xml_declaration=True)
