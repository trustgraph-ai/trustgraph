import React, { useState, useRef } from "react";

import { Upload, FilePlus } from "lucide-react";

import { Portal, Button, Dialog, Box, CloseButton } from "@chakra-ui/react";

import { useKnowledgeCores } from "@trustgraph/react-state";
import { useSettings } from "@trustgraph/react-state";
import { createAuthenticatedFetch } from "../../api/authenticated-fetch";
import TextField from "../common/TextField";

const UploadDialog = ({ open, onOpenChange }) => {
  const [files, setFiles] = useState([]);
  const [id, setId] = useState("");

  const knowledgeCoresState = useKnowledgeCores();
  const { settings } = useSettings();

  const fl2a = (x: FileList | null): File[] => {
    if (x) return Array.from(x);
    else return [];
  };

  const fileInput = useRef(null);
  const contentRef = useRef<HTMLDivElement>(null);

  const upload = () => {
    // Submit button is disabled, shouldn't happen
    if (files.length == 0) return;

    // Only 1 file can be selected
    const file = files[0];

    const url =
      "/api/import-core?" +
      "id=" +
      encodeURIComponent(id) +
      "&user=" +
      encodeURIComponent("trustgraph");

    // Use authenticated fetch with current API key
    const authenticatedFetch = createAuthenticatedFetch(
      settings.authentication.apiKey,
    );

    authenticatedFetch(url, {
      method: "POST",
      body: file,
    })
      .then(() => {
        console.log("Upload success.");
        setFiles([]);
        setId("");
        onOpenChange(false);
        // Refresh the knowledge cores list
        knowledgeCoresState.refetch();
      })
      .catch((error) => {
        console.error("Upload failed:", error);
        // TODO: Show error notification to user
      });
  };

  return (
    <Dialog.Root
      placement="center"
      open={open}
      onOpenChange={(x) => {
        onOpenChange(x.open);
      }}
    >
      <Portal>
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content ref={contentRef}>
            <Dialog.Header>
              <Dialog.Title>Upload Knowledge Core</Dialog.Title>
            </Dialog.Header>
            <Dialog.Body>
              <TextField
                label="Knowledge core ID"
                helperText="Use a unique ID for the core"
                value={id}
                onValueChange={setId}
              />

              <Box mt={5}>
                <Button
                  variant="solid"
                  colorPalette="primary"
                  onClick={() => fileInput.current.click()}
                >
                  <FilePlus /> Select file
                </Button>

                <input
                  ref={fileInput}
                  type="file"
                  onChange={(event) => setFiles(fl2a(event.target.files))}
                  style={{
                    clip: "rect(0 0 0 0)",
                    clipPath: "inset(50%)",
                    overflow: "hidden",
                    position: "absolute",
                    bottom: 0,
                    left: 0,
                    whiteSpace: "nowrap",
                    width: 1,
                  }}
                />
              </Box>

              {files.length > 0 && (
                <Box mt={3}>
                  <Box>Selected: {files[0].name}</Box>
                </Box>
              )}
            </Dialog.Body>
            <Dialog.Footer>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button
                onClick={() => upload()}
                colorPalette="primary"
                disabled={files.length < 1 || !id}
              >
                <Upload /> Load
              </Button>
            </Dialog.Footer>
            <Dialog.CloseTrigger asChild>
              <CloseButton size="sm" />
            </Dialog.CloseTrigger>
          </Dialog.Content>
        </Dialog.Positioner>
      </Portal>
    </Dialog.Root>
  );
};

export default UploadDialog;
