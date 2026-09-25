# Aspose.Email FOSS for Python

[![PyPI](https://img.shields.io/pypi/v/aspose-email-foss.svg)](https://pypi.org/project/aspose-email-foss/) ![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Contributors](https://img.shields.io/github/contributors/aspose-email-foss/Aspose.Email-FOSS-for-Python)](https://github.com/aspose-email-foss/Aspose.Email-FOSS-for-Python/graphs/contributors)

[![Aspose.Email FOSS for Python](https://products.aspose.org/media/email/python/banner-readme.png)](https://products.aspose.org/email/python/)

Aspose.Email FOSS for Python reads and writes Microsoft Outlook message formats including `.msg` and `.eml`, converting between MAPI and standard email representations. It solves interoperability problems for developers who need to process email archives, attachments, and properties without relying on Microsoft Outlook or commercial libraries. Users in email migration, compliance, and automation workflows use it to inspect, transform, and store email data using the `email_foss.cfb` and `email_foss.msg` modules. The package is open source under the MIT license, requires Python 3.10 or later, and has no external dependencies.

## Navigation

- [At a Glance](#at-a-glance)
- [Key Capabilities](#key-capabilities)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [Quick Start](#quick-start)
- [Additional Examples](#additional-examples)
- [API Reference](#api-reference)
- [Documentation & Resources](#documentation--resources)
- [Scope and Limitations](#scope-and-limitations)
- [Development and Testing](#development-and-testing)
- [License](#license)

## At a Glance

```mermaid
flowchart TD
  subgraph StartingPoints["Starting Points"]
    direction LR
    i1["An existing EML or MSG file"]
  end
  PRODUCT["Aspose.Email FOSS for Python"]
  subgraph Capabilities["Core Capabilities"]
    direction LR
    subgraph capl[" "]
      direction TB
      c1["Read MSG files"]
      c2["Write MSG files"]
      c3["Convert MSG to EML"]
    end
    subgraph capr[" "]
      direction TB
      c4["Convert EML to MSG"]
      c5["Low-level CFB access"]
      c6["MAPI property support"]
    end
  end
  subgraph Outputs["Outputs"]
    direction TB
    o1["MSG file"]
  end
  StartingPoints --> PRODUCT --> Capabilities --> Outputs
```

## Key Capabilities

- **Read MSG files.** Read MSG files by loading a `.msg` file into a `MapiMessage` instance and accessing its subject and other properties directly.
- **Write MSG files.** Write MSG files by creating a `MapiMessage` programmatically, setting sender and recipient properties, adding attachments, and saving the result to disk.
- **Convert MSG to EML.** Convert MSG to EML by loading a `.msg` file with `MapiMessage`, transforming it to an email message, and writing the resulting bytes to an `.eml` file.
- **Convert EML to MSG.** Convert EML to MSG by parsing an `.eml` file into an email message object, converting it to a `MapiMessage`, and saving it as a `.msg` file.
- **Low-level CFB access.** Inspect and construct Compound File Binary structures through `CFBReader` and `CFBWriter`, enabling direct access to internal MSG storage layouts.
- **Low-level MSG access.** Access MSG file internals such as attachment and recipient storages using `MsgReader` and `MsgWriter` without relying on higher-level abstractions.
- **MAPI property support.** Set and retrieve standard and custom MAPI properties including sender information using property identifiers and named property support.
- **Attachment handling.** Manage attachments by adding them from raw bytes or embedded messages, and inspecting their type and storage metadata.

## Installation

Install the published package from PyPI (`aspose-email-foss`, version 26.3):

```bash
pip install aspose-email-foss
```

To work from a source checkout instead, install the clone with pip:

```bash
git clone https://github.com/aspose-email-foss/Aspose.Email-FOSS-for-Python.git
cd Aspose.Email-FOSS-for-Python
pip install .
```

Verify the install:

```bash
python -c "import aspose.email_foss"
```

The package declares `python_requires` as `>=3.10`.

## Dependencies

### Required Package Dependencies

No required third-party package dependencies; in `pyproject.toml`, no `project.dependencies` is declared.

### Native and System Requirements

- Requires Python 3.10 or later (`python_requires=">=3.10"` in `pyproject.toml`).

## Quick Start

Read the subject line from an existing MSG file using the `MapiMessage` class and print it to the console.

```python
from aspose.email_foss import msg

with msg.MapiMessage.from_file("sample.msg") as message:
    print(message.subject)
```

Create a new `MapiMessage`, set sender properties, add a recipient and attachment, save it as MSG, then load and convert it to an email message for export as EML.

```python
from aspose.email_foss import msg

message = msg.MapiMessage.create("Hello", "Body")
message.set_property(msg.PropertyId.SENDER_NAME, "Alice")
message.set_property(msg.PropertyId.SENDER_EMAIL_ADDRESS, "alice@example.com")
message.add_recipient("bob@example.com", display_name="Bob")
message.add_attachment("note.txt", b"abc", mime_type="text/plain")
message.save("hello.msg")

with msg.MapiMessage.from_file("hello.msg") as loaded:
    email_message = loaded.to_email_message()
    with open("hello.eml", "wb") as target:
        target.write(email_message.as_bytes())
```

## Additional Examples

Create, convert, and inspect email messages and structured storage using Aspose.Email FOSS for Python.

### Create and read a structured storage stream using CFB APIs

```python
from aspose.email_foss.cfb import CFBDocument, CFBReader, CFBStorage, CFBStream, CFBWriter, ROOT_ENTRY_NAME

root = CFBStorage(ROOT_ENTRY_NAME)
root.add_stream(CFBStream("Summary", b"hello"))

data = CFBWriter.to_bytes(CFBDocument(root=root, major_version=3))
reader = CFBReader(data)
entry = reader.resolve_path(["Summary"])
print(reader.get_stream_data(entry.stream_id))
```

<details>
<summary>View Additional Examples</summary>

### Convert MSG to EML by reading a file and writing bytes

```python
from aspose.email_foss import msg

with msg.MapiMessage.from_file("message.msg") as message:
    email_message = message.to_email_message()

with open("message.eml", "wb") as target:
    target.write(email_message.as_bytes())
```

### Convert EML to MSG by parsing an email and saving it

```python
from email import policy
from email.parser import BytesParser

from aspose.email_foss import msg

with open("message.eml", "rb") as source:
    email_message = BytesParser(policy=policy.default).parse(source)

message = msg.MapiMessage.from_email_message(email_message)
message.save("message.msg")
```


Full runnable examples are available under [`examples/`](examples/) (see
[`examples/README.md`](examples/README.md) for a task-to-script index).

</details>

## API Reference

Aspose.Email FOSS for Python provides high-level and low-level APIs for working with email formats, with the high-level MSG API centered on `MapiMessage` for message creation and conversion, and the low-level MSG and CFB APIs offering direct access to property streams and Compound File Binary containers respectively.

The verified public surface has 30 types.

<details>
<summary>View the Complete Public API Surface</summary>

### Core API

| Class | Description |
| --- | --- |
| `CFBDocument` | Mutable Compound File Binary (CFB) document description. |
| `CFBError` | Raised for malformed or unsupported Compound File Binary (CFB) content. |
| `CFBReader` | Reusable reader for Compound File Binary (CFB) containers. |
| `CFBStorage` | Mutable storage node used by the CFB writer. |
| `CFBStream` | Mutable stream node used by the CFB writer. |
| `CFBWriter` | Deterministic serializer for Compound File Binary (CFB) containers. |
| `DirectoryEntry` | Fixed-size directory record for one storage/stream object and its tree links. |
| `Header` | Header record at file offset 0 defining Compound File Binary (CFB) geometry and allocation chain entry points. |
| `MapiAttachment` | Mutable attachment object. |
| `MapiMessage` | Mutable high-level MSG object with MSG and EmailMessage conversion support. |
| `MapiNamedProperty` | Identifier for a named MAPI property. |
| `MapiProperty` | Logical MAPI property with optional named-property identity. |
| `MapiRecipient` | Mutable recipient object. |
| `MsgDocument` | Mutable MSG document model that can be serialized through the CFB writer. |
| `MsgError` | Raised for malformed or unsupported MSG structures. |
| `MsgReader` | Normative top-level MSG containment and stream requirements for container traversal. |
| `MsgStorage` | Mutable MSG storage node with role classification and parsed property-stream metadata. |
| `MsgStream` | Mutable MSG stream node with raw bytes and CFB metadata. |
| `MsgWriter` | Serializer that writes a MsgDocument into a CFB-backed .msg payload. |
| `PropertyEntryFixedLength` | Fixed-length property stream entry containing property tag, flags, and inline 8-byte value payload. |
| `PropertyStreamHeaderSubobject` | Property stream header used in recipient and attachment storages, containing only reserved bytes. |
| `PropertyStreamHeaderTopLevel` | Top-level property stream header containing next-id counters and counts for recipients and attachments. |
| `StorageLayout` | Naming and containment rules for recipient, attachment, embedded message, and nameid storages. |
| `MapiPropertyCollection` | The MapiPropertyCollection class represents a collection of MAPI properties associated with a MapiMessage, providing methods to add, get, set, and remove individual properties by their identifier. |

#### Enumerations

| Enumeration | Description |
| --- | --- |
| `DirectoryColorFlag` | Stores the red-black tree color used by directory sibling links. |
| `DirectoryObjectType` | Classifies the directory entry payload as unallocated, storage, stream, or root storage. |
| `SectorMarker` | Special FAT marker values reserved for sector allocation metadata. |
| `CommonMessagePropertyId` | Common MAPI property identifiers used by the MSG reader/writer for core message semantics. |
| `PropertyId` | Common property identifiers paired with their default MAPI property types. |
| `PropertyTypeCode` | MAPI property type codes used in MSG property tags and value stream names. |

#### Detailed Member Reference

### email_foss

The top-level `email_foss` module serves as the package entry point, exposing the high-level MSG API centered on `MapiMessage` and the low-level MSG and CFB modules for direct property-stream and container access.

### cfb

The `email_foss.cfb` module provides the low-level CFB API for reading and writing Compound File Binary containers, with `CFBReader` and `CFBWriter` handling parsing and serialization, and `CFBDocument`, `CFBStorage`, and `CFBStream` representing the container structure.

### msg

The `email_foss.msg` module provides both high-level and low-level MSG APIs, with `MapiMessage` supporting message creation and conversion, and `MsgReader`, `MsgWriter`, and `MsgDocument` enabling direct access to property streams and subobject structures.

### MapiAttachment

`MapiAttachment` represents an attachment in a `MapiMessage`, supporting embedded messages and storage attachments with methods to create, inspect, and modify attachment properties.

- `embedded_storage_name`: Defined as `def embedded_storage_name(self) -> str / None`.
- `from_bytes`: Defined as `def from_bytes(cls, filename: str, data: bytes, *, mime_type: str / None=None, content_id: str / None=None) -> 'MapiAttachment'`.
- `from_embedded_message`: Defined as `def from_embedded_message(cls, message: 'MapiMessage', *, filename: str / None=None, mime_type: str / None=None) -> 'MapiAttachment'`.
- `is_embedded_message`: Defined as `def is_embedded_message(self) -> bool`.
- `is_storage_attachment`: Defined as `def is_storage_attachment(self) -> bool`.
- `set_property`: Defined as `def set_property(self, property_id: int / CommonMessagePropertyId / PropertyId, property_type_or_value: int / PropertyTypeCode / Any, value: Any=_MISSING, *, flags: int=DEFAULT_PROPERTY_FLAGS) -> MapiProperty`.
- `storage_name`: Defined as `def storage_name(self) -> str / None`.

### MsgReader

`MsgReader` parses MSG files and provides access to property streams, recipient storages, attachment storages, and the underlying CFB structure through its `cfb_reader` property.

- `cfb_reader`: Defined as `def cfb_reader(self) -> CFBReader`.
- `close`: Defined as `def close(self) -> None`.
- `from_file`: Defined as `def from_file(cls, path: Path / str, *, strict: bool=False) -> 'MsgReader'`.
- `iter_attachment_storages`: Defined as `def iter_attachment_storages(self) -> Iterator[DirectoryEntry]`.
- `iter_recipient_storages`: Defined as `def iter_recipient_storages(self) -> Iterator[DirectoryEntry]`.
- `iter_top_level_fixed_length_properties`: Defined as `def iter_top_level_fixed_length_properties(self) -> Iterator[PropertyEntryFixedLength]`.
- `parse_message_property_stream`: Read the property stream in the top level or an embedded-message storage.
- `parse_subobject_property_stream`: Read the property stream in recipient/attachment storage and decode fixed-length entries.
- `parse_subobject_property_stream_data`: Decode recipient/attachment property stream header and fixed-length entries.
- `parse_top_level_property_stream`: Decode top-level property stream header and fixed-length entries.
- `storage_layout`: Defined as `def storage_layout(self) -> StorageLayout`.
- `strict`: Defined as `def strict(self) -> bool`.
- `validation_issues`: Defined as `def validation_issues(self) -> Tuple[str, ...]`.

### MsgWriter

`MsgWriter` serializes `MapiMessage` objects to MSG files, supporting output to bytes or file paths while preserving the MSG format structure.

- `to_bytes`: Defined as `def to_bytes(cls, document: MsgDocument) -> bytes`.
- `write_file`: Defined as `def write_file(cls, document: MsgDocument, path: Path / str) -> None`.

### CFBReader

`CFBReader` parses Compound File Binary files and exposes container metadata such as `sector_size`, `major_version`, and `directory_entry_count`, along with methods to navigate the internal structure.

- `close`: Defined as `def close(self) -> None`.
- `data_size`: Defined as `def data_size(self) -> int`.
- `directory_entry_count`: Defined as `def directory_entry_count(self) -> int`.
- `fat_sector_count`: Defined as `def fat_sector_count(self) -> int`.
- `file_size`: Defined as `def file_size(self) -> int`.
- `find_child_by_name`: Defined as `def find_child_by_name(self, storage_stream_id: StreamId, name: str) -> Optional[DirectoryEntry]`.
- `from_file`: Defined as `def from_file(cls, path: Path / str) -> 'CFBReader'`.
- `get_entry`: Defined as `def get_entry(self, stream_id: StreamId) -> DirectoryEntry`.
- `get_stream_data`: Defined as `def get_stream_data(self, stream_id: StreamId) -> bytes`.
- `iter_children`: Defined as `def iter_children(self, storage_stream_id: StreamId) -> Iterator[DirectoryEntry]`.
- `iter_storages`: Defined as `def iter_storages(self) -> Iterator[DirectoryEntry]`.
- `iter_streams`: Defined as `def iter_streams(self) -> Iterator[DirectoryEntry]`.
- `iter_tree`: Yield a depth-first tree traversal as (depth, entry) tuples.
- `major_version`: Defined as `def major_version(self) -> int`.
- `materialized_stream_count`: Defined as `def materialized_stream_count(self) -> int`.
- `mini_sector_size`: Defined as `def mini_sector_size(self) -> int`.
- `resolve_path`: Resolve a storage/stream path by exact directory-entry names.
- `sector_size`: Defined as `def sector_size(self) -> int`.

### CFBWriter

`CFBWriter` constructs Compound File Binary containers in memory and can serialize them to bytes or write them directly to a file path.

- `to_bytes`: Defined as `def to_bytes(cls, document: CFBDocument) -> bytes`.
- `write_file`: Defined as `def write_file(cls, document: CFBDocument, path: Path / str) -> None`.

### MsgError

`MsgError` is raised when parsing or processing MSG files encounters issues that prevent successful completion.

### CFBError

`CFBError` is raised when parsing or writing Compound File Binary files encounters structural or format issues.

### PropertyId

`PropertyId` defines the numeric identifiers used to reference properties in MSG property streams, such as SENDER_NAME and SENDER_EMAIL_ADDRESS.

### MapiNamedProperty

`MapiNamedProperty` represents a named property in MSG files, storing either a numeric identifier or a string name along with its value.

- `numeric`: Defined as `def numeric(cls, lid: int, property_set: uuid.UUID / str) -> 'MapiNamedProperty'`.
- `string`: Defined as `def string(cls, name: str, property_set: uuid.UUID / str=PS_PUBLIC_STRINGS) -> 'MapiNamedProperty'`.

</details>

## Documentation & Resources

- **[Getting started guide](https://docs.aspose.org/email/python/)** — The getting started guide introduces the core concepts and basic usage patterns for creating and manipulating email messages with Aspose.Email FOSS for Python, including initialization, property access, and file I/O operations.
- **[How-to guides & FAQ](https://kb.aspose.org/email/python/)** — The how-to guides and FAQ provide practical examples and answers for common tasks such as parsing message files, handling attachments, and working with message properties in Aspose.Email FOSS for Python.
- **[Full API reference](https://reference.aspose.org/email/python/)** — The full API reference documents all public classes, methods, and constants available in Aspose.Email FOSS for Python, including `MapiMessage`, `PropertyId`, and related members. It covers all 30 verified public types; the [API Reference](#api-reference) section above covers the essentials.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-email-foss/Aspose.Email-FOSS-for-Python/issues).

## Scope and Limitations

Aspose.Email FOSS for Python provides programmatic handling of local CFB and MSG files, conversion to and from EML via Python's built-in email package, and generic access to MAPI properties through the `MapiMessage` class and its members.

- The library does not support connecting to mail servers and lacks IMAP, SMTP, and POP3 functionality, as it operates solely on local files and in-memory message objects.
- TNEF (Transport Neutral Encapsulation Format, commonly encountered as `winmail.dat` attachments) is not parsed or generated by this library.
- There is no dedicated calendar or appointment API; calendar-specific MAPI properties can only be accessed generically using `set_property` and `get_property_value` methods.
- Direct parsing of `.eml` files is not implemented; EML support relies on `MapiMessage.from_email_message` and `to_email_message` in combination with Python's `email.parser` and `email.message.EmailMessage`.

These limitations don't apply to [Aspose.Email for Python — Enterprise Edition](https://products.aspose.com/email/python-net/). Aspose.Email FOSS for Python provides open-source access to core email processing capabilities, while Aspose.Email commercial edition extends this with additional formats, advanced features, and commercial support.

## Development and Testing

Build and test Aspose.Email FOSS for Python using the tests in tests/, examples in examples/, and CI workflows in .github/workflows/; the package requires Python >=3.10 and is licensed under MIT.

The suite covers 2 test files under `tests/`. Releases run through the [release workflow](.github/workflows/release.yml).

## License

This project is licensed under the [MIT License](LICENSE). The MIT License permits use, copying, modification, distribution, sublicensing, and commercial use, provided its copyright and permission notice are retained. The software is provided without warranty.
