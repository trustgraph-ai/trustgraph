import React from "react";

import { useLoadStateStore } from "@trustgraph/react-state";
import ChipInputField from "../common/ChipInputField";

const Keywords = () => {
  const values = useLoadStateStore((state) => state.keywords);
  const setValues = useLoadStateStore((state) => state.setKeywords);

  return (
    <ChipInputField
      label="Keywords"
      required={false}
      values={values}
      onValuesChange={setValues}
    />
  );
};

export default Keywords;
