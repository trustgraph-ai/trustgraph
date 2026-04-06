import React from "react";
import { HandCoins } from "lucide-react";

import PageHeader from "../components/common/PageHeader";
import TokenCosts from "../components/token-cost/TokenCosts";

const TokenCostPage = () => {
  return (
    <>
      <PageHeader
        icon={<HandCoins />}
        title="Token Cost Configuration"
        description="Define the cost of AI token processing"
      />
      <TokenCosts />
    </>
  );
};

export default TokenCostPage;
