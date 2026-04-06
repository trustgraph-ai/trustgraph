import React, { useMemo } from "react";
import SelectField, { SelectFieldValue } from "../common/SelectField";

// Comprehensive XSD datatype definitions
const XSD_DATATYPES = [
  // Text and String Types
  {
    value: "xsd:string",
    label: "String",
    category: "Text",
    description: "Unicode character sequence",
  },
  {
    value: "xsd:normalizedString",
    label: "Normalized String",
    category: "Text",
    description: "String with normalized whitespace",
  },
  {
    value: "xsd:token",
    label: "Token",
    category: "Text",
    description: "String without leading/trailing whitespace",
  },
  {
    value: "xsd:language",
    label: "Language Code",
    category: "Text",
    description: "RFC 3066 language identifier (e.g., en-US)",
  },

  // Numeric Types - Integers
  {
    value: "xsd:integer",
    label: "Integer",
    category: "Numbers",
    description: "Arbitrary precision integer",
  },
  {
    value: "xsd:int",
    label: "32-bit Integer",
    category: "Numbers",
    description: "32-bit signed integer (-2,147,483,648 to 2,147,483,647)",
  },
  {
    value: "xsd:long",
    label: "64-bit Integer",
    category: "Numbers",
    description: "64-bit signed integer",
  },
  {
    value: "xsd:short",
    label: "16-bit Integer",
    category: "Numbers",
    description: "16-bit signed integer (-32,768 to 32,767)",
  },
  {
    value: "xsd:byte",
    label: "8-bit Integer",
    category: "Numbers",
    description: "8-bit signed integer (-128 to 127)",
  },
  {
    value: "xsd:positiveInteger",
    label: "Positive Integer",
    category: "Numbers",
    description: "Integer greater than zero",
  },
  {
    value: "xsd:nonNegativeInteger",
    label: "Non-negative Integer",
    category: "Numbers",
    description: "Integer greater than or equal to zero",
  },
  {
    value: "xsd:negativeInteger",
    label: "Negative Integer",
    category: "Numbers",
    description: "Integer less than zero",
  },

  // Numeric Types - Decimals
  {
    value: "xsd:decimal",
    label: "Decimal",
    category: "Numbers",
    description: "Arbitrary precision decimal number",
  },
  {
    value: "xsd:float",
    label: "Float",
    category: "Numbers",
    description: "32-bit floating point number",
  },
  {
    value: "xsd:double",
    label: "Double",
    category: "Numbers",
    description: "64-bit floating point number",
  },

  // Date and Time
  {
    value: "xsd:dateTime",
    label: "Date and Time",
    category: "Date/Time",
    description: "Complete date and time (YYYY-MM-DDTHH:MM:SS)",
  },
  {
    value: "xsd:date",
    label: "Date",
    category: "Date/Time",
    description: "Calendar date (YYYY-MM-DD)",
  },
  {
    value: "xsd:time",
    label: "Time",
    category: "Date/Time",
    description: "Time of day (HH:MM:SS)",
  },
  {
    value: "xsd:gYear",
    label: "Year",
    category: "Date/Time",
    description: "Gregorian calendar year (YYYY)",
  },
  {
    value: "xsd:gMonth",
    label: "Month",
    category: "Date/Time",
    description: "Gregorian calendar month (--MM)",
  },
  {
    value: "xsd:gDay",
    label: "Day",
    category: "Date/Time",
    description: "Gregorian calendar day (---DD)",
  },
  {
    value: "xsd:duration",
    label: "Duration",
    category: "Date/Time",
    description: "Time duration (P1Y2M3DT4H5M6S)",
  },

  // Boolean and Binary
  {
    value: "xsd:boolean",
    label: "Boolean",
    category: "Other",
    description: "True or false value",
  },
  {
    value: "xsd:base64Binary",
    label: "Base64 Binary",
    category: "Other",
    description: "Base64-encoded binary data",
  },
  {
    value: "xsd:hexBinary",
    label: "Hex Binary",
    category: "Other",
    description: "Hexadecimal-encoded binary data",
  },

  // URIs and References
  {
    value: "xsd:anyURI",
    label: "URI",
    category: "Other",
    description: "Uniform Resource Identifier",
  },
];

interface XSDDatatypeSelectorProps {
  label: string;
  value: string;
  onValueChange: (value: string) => void;
  contentRef?: React.RefObject<HTMLElement>;
}

const XSDDatatypeSelector: React.FC<XSDDatatypeSelectorProps> = ({
  label,
  value,
  onValueChange,
  contentRef,
}) => {
  // Transform XSD datatypes into SelectFieldValue format with rich labels
  const items: SelectFieldValue[] = useMemo(
    () =>
      XSD_DATATYPES.map((dt) => ({
        value: dt.value,
        label: `${dt.label} (${dt.value})`,
        description: dt.description,
      })),
    [],
  );

  return (
    <SelectField
      label={label}
      items={items}
      value={[value]}
      onValueChange={(values) => onValueChange(values[0] || "")}
      contentRef={contentRef}
    />
  );
};

export default XSDDatatypeSelector;
