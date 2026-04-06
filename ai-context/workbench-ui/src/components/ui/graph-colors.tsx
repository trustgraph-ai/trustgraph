import { useColorModeValue } from "../ui/color-mode";

import { system } from "../../theme";

// Theme-aware colors that respond to light/dark mode
export const useBorderColor = () =>
  useColorModeValue(
    system.token("colors.gray.300"), // light mode
    system.token("colors.gray.600"), // dark mode
  );

export const useBackgroundColor = () =>
  useColorModeValue(
    system.token("colors.gray.50"), // light mode
    system.token("colors.gray.800"), // dark mode
  );

export const useNodeColor = () =>
  useColorModeValue(
    system.token("colors.gray.800"), // light mode
    system.token("colors.gray.100"), // dark mode
  );

export const useNodeTextColor = () =>
  useColorModeValue(
    system.token("colors.mintCream.700"), // light mode
    system.token("colors.mintCream.300"), // dark mode
  );

export const useSelectedNodeTextColor = () =>
  useColorModeValue(
    system.token("colors.warmOrange.700"), // light mode
    system.token("colors.warmOrange.300"), // dark mode
  );

export const useLinkColor = () =>
  useColorModeValue(
    system.token("colors.gray.500"), // light mode
    system.token("colors.gray.500"), // dark mode
  );

export const useLinkTextColor = () =>
  useColorModeValue(
    system.token("colors.yellowNeutral.700"), // light mode
    system.token("colors.yellowNeutral.300"), // dark mode
  );

export const useLinkParticleColor = () =>
  useColorModeValue(
    system.token("colors.deepPlum.700"), // light mode
    system.token("colors.deepPlum.600"), // dark mode
  );
