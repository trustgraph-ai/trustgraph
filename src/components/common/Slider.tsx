import React from "react";

import { Field, Slider as ChakraSlider } from "@chakra-ui/react";

interface SliderProps {
  label: string;
  minValue: number;
  maxValue: number;
  value: number;
  step: number;
  onValueChange: (x: number) => void;
}

const Slider: React.FC<SliderProps> = ({
  label,
  minValue,
  maxValue,
  value,
  onValueChange,
  step,
}) => {
  return (
    <Field.Root mb={4}>
      <Field.Label fontWeight="medium">{label}</Field.Label>
      <ChakraSlider.Root
        min={minValue}
        max={maxValue}
        step={step}
        value={[value]}
        onValueChange={(e) => onValueChange(e.value[0])}
        width="100%"
      >
        <ChakraSlider.ValueText />
        <ChakraSlider.Control>
          <ChakraSlider.Track bg="{colors.primary.muted}">
            <ChakraSlider.Range bg="{colors.primary.solid}" />
          </ChakraSlider.Track>
          <ChakraSlider.Thumbs rounded={11} />
        </ChakraSlider.Control>
      </ChakraSlider.Root>
    </Field.Root>
  );
};

export default Slider;
