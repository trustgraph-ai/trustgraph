import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import BasicTable from "../BasicTable";

// Mock Chakra UI components
vi.mock("@chakra-ui/react", () => ({
  Table: {
    Root: ({ children }: React.PropsWithChildren) => (
      <table data-testid="table-root">{children}</table>
    ),
    Header: ({ children }: React.PropsWithChildren) => (
      <thead data-testid="table-header">{children}</thead>
    ),
    Body: ({ children }: React.PropsWithChildren) => (
      <tbody data-testid="table-body">{children}</tbody>
    ),
    Row: ({ children }: React.PropsWithChildren) => (
      <tr data-testid="table-row">{children}</tr>
    ),
    ColumnHeader: ({ children }: React.PropsWithChildren) => (
      <th data-testid="table-column-header">{children}</th>
    ),
    Cell: ({ children }: React.PropsWithChildren) => (
      <td data-testid="table-cell">{children}</td>
    ),
  },
}));

// Mock TanStack React Table
vi.mock("@tanstack/react-table", () => ({
  flexRender: vi.fn((content) => content),
}));

describe("BasicTable", () => {
  const mockTable = {
    getHeaderGroups: vi.fn(),
    getRowModel: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should render table structure", () => {
    mockTable.getHeaderGroups.mockReturnValue([]);
    mockTable.getRowModel.mockReturnValue({ rows: [] });

    render(<BasicTable table={mockTable} />);

    expect(screen.getByTestId("table-root")).toBeInTheDocument();
    expect(screen.getByTestId("table-header")).toBeInTheDocument();
    expect(screen.getByTestId("table-body")).toBeInTheDocument();
  });

  it("should render header groups", () => {
    const mockHeaderGroups = [
      {
        id: "header-group-1",
        headers: [
          {
            id: "header-1",
            isPlaceholder: false,
            column: {
              columnDef: {
                header: "Column 1",
              },
            },
            getContext: () => ({}),
          },
          {
            id: "header-2",
            isPlaceholder: false,
            column: {
              columnDef: {
                header: "Column 2",
              },
            },
            getContext: () => ({}),
          },
        ],
      },
    ];

    mockTable.getHeaderGroups.mockReturnValue(mockHeaderGroups);
    mockTable.getRowModel.mockReturnValue({ rows: [] });

    render(<BasicTable table={mockTable} />);

    expect(screen.getByText("Column 1")).toBeInTheDocument();
    expect(screen.getByText("Column 2")).toBeInTheDocument();
  });

  it("should not render placeholder headers", () => {
    const mockHeaderGroups = [
      {
        id: "header-group-1",
        headers: [
          {
            id: "header-1",
            isPlaceholder: true,
            column: {
              columnDef: {
                header: "Placeholder Column",
              },
            },
            getContext: () => ({}),
          },
          {
            id: "header-2",
            isPlaceholder: false,
            column: {
              columnDef: {
                header: "Visible Column",
              },
            },
            getContext: () => ({}),
          },
        ],
      },
    ];

    mockTable.getHeaderGroups.mockReturnValue(mockHeaderGroups);
    mockTable.getRowModel.mockReturnValue({ rows: [] });

    render(<BasicTable table={mockTable} />);

    expect(screen.queryByText("Placeholder Column")).not.toBeInTheDocument();
    expect(screen.getByText("Visible Column")).toBeInTheDocument();
  });

  it("should render table rows", () => {
    const mockRows = [
      {
        id: "row-1",
        getVisibleCells: () => [
          {
            id: "cell-1",
            column: {
              columnDef: {
                cell: "Cell 1",
              },
            },
            getContext: () => ({}),
          },
          {
            id: "cell-2",
            column: {
              columnDef: {
                cell: "Cell 2",
              },
            },
            getContext: () => ({}),
          },
        ],
      },
    ];

    mockTable.getHeaderGroups.mockReturnValue([]);
    mockTable.getRowModel.mockReturnValue({ rows: mockRows });

    render(<BasicTable table={mockTable} />);

    expect(screen.getByText("Cell 1")).toBeInTheDocument();
    expect(screen.getByText("Cell 2")).toBeInTheDocument();
  });

  it("should render multiple rows", () => {
    const mockRows = [
      {
        id: "row-1",
        getVisibleCells: () => [
          {
            id: "cell-1-1",
            column: {
              columnDef: {
                cell: "Row 1 Cell 1",
              },
            },
            getContext: () => ({}),
          },
        ],
      },
      {
        id: "row-2",
        getVisibleCells: () => [
          {
            id: "cell-2-1",
            column: {
              columnDef: {
                cell: "Row 2 Cell 1",
              },
            },
            getContext: () => ({}),
          },
        ],
      },
    ];

    mockTable.getHeaderGroups.mockReturnValue([]);
    mockTable.getRowModel.mockReturnValue({ rows: mockRows });

    render(<BasicTable table={mockTable} />);

    expect(screen.getByText("Row 1 Cell 1")).toBeInTheDocument();
    expect(screen.getByText("Row 2 Cell 1")).toBeInTheDocument();
  });

  it("should render complete table with headers and rows", () => {
    const mockHeaderGroups = [
      {
        id: "header-group-1",
        headers: [
          {
            id: "header-1",
            isPlaceholder: false,
            column: {
              columnDef: {
                header: "Name",
              },
            },
            getContext: () => ({}),
          },
          {
            id: "header-2",
            isPlaceholder: false,
            column: {
              columnDef: {
                header: "Age",
              },
            },
            getContext: () => ({}),
          },
        ],
      },
    ];

    const mockRows = [
      {
        id: "row-1",
        getVisibleCells: () => [
          {
            id: "cell-1-1",
            column: {
              columnDef: {
                cell: "John",
              },
            },
            getContext: () => ({}),
          },
          {
            id: "cell-1-2",
            column: {
              columnDef: {
                cell: "25",
              },
            },
            getContext: () => ({}),
          },
        ],
      },
      {
        id: "row-2",
        getVisibleCells: () => [
          {
            id: "cell-2-1",
            column: {
              columnDef: {
                cell: "Jane",
              },
            },
            getContext: () => ({}),
          },
          {
            id: "cell-2-2",
            column: {
              columnDef: {
                cell: "30",
              },
            },
            getContext: () => ({}),
          },
        ],
      },
    ];

    mockTable.getHeaderGroups.mockReturnValue(mockHeaderGroups);
    mockTable.getRowModel.mockReturnValue({ rows: mockRows });

    render(<BasicTable table={mockTable} />);

    // Check headers
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Age")).toBeInTheDocument();

    // Check rows
    expect(screen.getByText("John")).toBeInTheDocument();
    expect(screen.getByText("25")).toBeInTheDocument();
    expect(screen.getByText("Jane")).toBeInTheDocument();
    expect(screen.getByText("30")).toBeInTheDocument();
  });

  it("should handle empty table", () => {
    mockTable.getHeaderGroups.mockReturnValue([]);
    mockTable.getRowModel.mockReturnValue({ rows: [] });

    render(<BasicTable table={mockTable} />);

    expect(screen.getByTestId("table-root")).toBeInTheDocument();
    expect(screen.getByTestId("table-header")).toBeInTheDocument();
    expect(screen.getByTestId("table-body")).toBeInTheDocument();
  });

  it("should handle table with headers but no rows", () => {
    const mockHeaderGroups = [
      {
        id: "header-group-1",
        headers: [
          {
            id: "header-1",
            isPlaceholder: false,
            column: {
              columnDef: {
                header: "Empty Table Header",
              },
            },
            getContext: () => ({}),
          },
        ],
      },
    ];

    mockTable.getHeaderGroups.mockReturnValue(mockHeaderGroups);
    mockTable.getRowModel.mockReturnValue({ rows: [] });

    render(<BasicTable table={mockTable} />);

    expect(screen.getByText("Empty Table Header")).toBeInTheDocument();
  });

  it("should handle table with rows but no headers", () => {
    const mockRows = [
      {
        id: "row-1",
        getVisibleCells: () => [
          {
            id: "cell-1",
            column: {
              columnDef: {
                cell: "Orphan Cell",
              },
            },
            getContext: () => ({}),
          },
        ],
      },
    ];

    mockTable.getHeaderGroups.mockReturnValue([]);
    mockTable.getRowModel.mockReturnValue({ rows: mockRows });

    render(<BasicTable table={mockTable} />);

    expect(screen.getByText("Orphan Cell")).toBeInTheDocument();
  });

  it("should handle multiple header groups", () => {
    const mockHeaderGroups = [
      {
        id: "header-group-1",
        headers: [
          {
            id: "header-1",
            isPlaceholder: false,
            column: {
              columnDef: {
                header: "Group 1 Header",
              },
            },
            getContext: () => ({}),
          },
        ],
      },
      {
        id: "header-group-2",
        headers: [
          {
            id: "header-2",
            isPlaceholder: false,
            column: {
              columnDef: {
                header: "Group 2 Header",
              },
            },
            getContext: () => ({}),
          },
        ],
      },
    ];

    mockTable.getHeaderGroups.mockReturnValue(mockHeaderGroups);
    mockTable.getRowModel.mockReturnValue({ rows: [] });

    render(<BasicTable table={mockTable} />);

    expect(screen.getByText("Group 1 Header")).toBeInTheDocument();
    expect(screen.getByText("Group 2 Header")).toBeInTheDocument();
  });
});
