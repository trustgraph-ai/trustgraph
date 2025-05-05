
import dataclasses
import datetime
from typing import List

@dataclasses.dataclass
class Triple:
    s : str
    p : str
    o : str

@dataclasses.dataclass
class ConfigKey:
    type : str
    key : str

@dataclasses.dataclass
class ConfigValue:
    type : str
    key : str
    value : str

@dataclasses.dataclass
class DocumentMetadata:
    id : str
    time : datetime.datetime
    kind : str
    title : str
    comments : str
    metadata : List[Triple]
    user : str
    tags : List[str]

@dataclasses.dataclass
class ProcessingMetadata:
    id : str
    document_id : str
    time : datetime.datetime
    flow : str
    user : str
    collection : str
    tags : List[str]
