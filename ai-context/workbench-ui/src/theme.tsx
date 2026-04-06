//
// The theme lives here.
//
// To theme this app, you need:
// - 5 colour ramps.  Easiest way to do this is to use the colour design
//   of our website.  Or use the background image, or screenshot the page.
//   Then feed it into coolors.co.  Image picker, and extra 5 colours
//   which work well together, and Export -> Open in generator.  You've got
//   5 base colours, but they'll need adjusting.  Feed them into Claude, and
//   ask Claude to make a colour ramp.  You can cut'n'paste a colour ramp
//   from this file from below to show Claude the structure to create.
//   That's 5 general theme colours sorted.
// - There are a few other colours which follow.  The graph UI can have
//   its own colours, but they need to be sympathetic to the overall
//   palette.
// - There are some colours which form the callouts for thinking, observing
//   and answer in the agent assistant.
// - After the colour ramps are defined there are palettes which specify
//   how the colours are used.  These specify combinations for dark/light
//   mode.
//
// Claude Code knows how to manage this file, given base colours, it can
// adjust everything that's here.

import { createSystem, defaultConfig, defineConfig } from "@chakra-ui/react";

export const config = defineConfig({
  //  strictTokens: true,
  globalCss: {
    "#root": {
      color: "{colors.text}",
      backgroundColor: "{colors.background}",
    },
    "html, body": {
      margin: 0,
      padding: 0,
    },
  },
  theme: {
    tokens: {
      colors: {
        // General theme colours, using a consistent palette e.g. made from
        // the company website or site design
        airForceBlue: {
          50: { value: "#EDF5F9" },
          100: { value: "#DBEAF3" },
          200: { value: "#B7D5E7" },
          300: { value: "#93C0DB" },
          400: { value: "#6FABCF" },
          500: { value: "#558BB4" }, // Base color
          600: { value: "#4A7BA2" },
          700: { value: "#3F6B90" },
          800: { value: "#345B7E" },
          900: { value: "#294B6C" },
        },
        skyBlue: {
          50: { value: "#F0F7FA" },
          100: { value: "#E1EFF5" },
          200: { value: "#C3DFEB" },
          300: { value: "#A5CFE1" },
          400: { value: "#94C3D7" },
          500: { value: "#83B7CE" }, // Base color
          600: { value: "#72A4BC" },
          700: { value: "#6191AA" },
          800: { value: "#507E98" },
          900: { value: "#3F6B86" },
        },
        deepPlum: {
          50: { value: "#F9F8F9" },
          100: { value: "#F3F1F3" },
          200: { value: "#E7E3E7" },
          300: { value: "#DBD5DB" },
          400: { value: "#CFC7CF" },
          500: { value: "#A394A3" }, // Lightened base for usability
          600: { value: "#7A6B7A" },
          700: { value: "#5C4D5C" },
          800: { value: "#3D2E3D" },
          900: { value: "#250219" }, // Original color
        },
        darkViolet: {
          50: { value: "#FAF9FB" },
          100: { value: "#F5F3F6" },
          200: { value: "#EBE7ED" },
          300: { value: "#E1DBE4" },
          400: { value: "#D7CFDB" },
          500: { value: "#9A7BA2" }, // Lightened base for usability
          600: { value: "#7A5B82" },
          700: { value: "#5F4268" },
          800: { value: "#4F2F56" },
          900: { value: "#3F1D44" }, // Original color
        },
        thistle: {
          50: { value: "#FDFCFE" },
          100: { value: "#FAF8FC" },
          200: { value: "#F5F0F9" },
          300: { value: "#F0E8F6" },
          400: { value: "#E5D4F1" },
          500: { value: "#DAC0EC" }, // Base color
          600: { value: "#C8A5E0" },
          700: { value: "#B68AD4" },
          800: { value: "#A46FC8" },
          900: { value: "#8B4FB5" },
        },

        // Extra colours which aren't part of the map

        // Desaturated orange

        // On medium-saturation orange, useful for accents where the
        // palette colours aren't provding accents.
        warmOrange: {
          50: { value: "#FEFAF8" },
          100: { value: "#FDF5F0" },
          200: { value: "#FBEBE1" },
          300: { value: "#F9E1D2" },
          400: { value: "#F8BF9B" },
          500: { value: "#F79D65" }, // Base color
          600: { value: "#F5853E" },
          700: { value: "#E66B1A" },
          800: { value: "#C55A15" },
          900: { value: "#A44A11" },
        },

        // A desaturated orange, this provides a more neutral base for
        // backgrounds - warmOrange is too saturated at the darker end
        warmNeutral: {
          50: { value: "#FDFCFB" },
          100: { value: "#FAF8F6" },
          200: { value: "#F5F1ED" },
          300: { value: "#EFEAE4" },
          400: { value: "#E0D5CA" },
          500: { value: "#D1C1B0" }, // Desaturated warm base
          600: { value: "#B8A394" },
          700: { value: "#9F8578" },
          800: { value: "#6B5B52" }, // Dark enough for backgrounds
          900: { value: "#3A312B" }, // Very dark warm neutral
        },

        // A desaturated yellow, harmonious with the orange
        yellowNeutral: {
          50: { value: "#FEFEF8" },
          100: { value: "#FCFCF0" },
          200: { value: "#F8F6E1" },
          300: { value: "#F3F0D2" },
          400: { value: "#E8E2B8" },
          500: { value: "#DDD49E" }, // Much more yellow and lighter
          600: { value: "#CFC284" },
          700: { value: "#BAA56A" },
          800: { value: "#8A7F52" }, // Lighter but still usable for backgrounds
          900: { value: "#5A5238" }, // Warmer yellow-brown
        },

        // Greens are useful for answers and success.  Here are some.
        sageGreen: {
          50: { value: "#F7FAF8" },
          100: { value: "#EFF5F1" },
          200: { value: "#DFEBE3" },
          300: { value: "#CFE1D5" },
          400: { value: "#B9D1BE" },
          500: { value: "#A4C2A8" }, // Base color
          600: { value: "#8FB394" },
          700: { value: "#7AA480" },
          800: { value: "#65956C" },
          900: { value: "#508658" },
        },
        neutralGreen: {
          50: { value: "#FDFEFD" },
          100: { value: "#EFF7F6" }, // Original color moved up
          200: { value: "#DEF0ED" },
          300: { value: "#CDE9E4" },
          400: { value: "#BCE2DB" },
          500: { value: "#9DD4CA" }, // Usable mid-tone
          600: { value: "#7EC6B9" },
          700: { value: "#5FB8A8" },
          800: { value: "#479085" }, // Slightly desaturated from #4A9A8A
          900: { value: "#337062" }, // Slightly desaturated from #357C6C
        },

        // Useful for off-white 'paper' colours.
        mintCream: {
          50: { value: "#FDFEFD" },
          100: { value: "#EFF7F6" }, // Original color moved up
          200: { value: "#DEF0ED" },
          300: { value: "#CDE9E4" },
          400: { value: "#BCE2DB" },
          500: { value: "#9DD4CA" }, // Usable mid-tone
          600: { value: "#7EC6B9" },
          700: { value: "#5FB8A8" },
          800: { value: "#4A9A8A" },
          900: { value: "#357C6C" },
        },

        // Slightly blue-gray
        gray: {
          50: { value: "#F7FAFC" }, // Lightest
          100: { value: "#EDF2F7" },
          200: { value: "#E2E8F0" },
          300: { value: "#CBD5E0" },
          400: { value: "#A0AEC0" },
          500: { value: "#718096" }, // Mid-gray
          600: { value: "#4A5568" },
          700: { value: "#2D3748" },
          800: { value: "#1A202C" },
          900: { value: "#171923" }, // Darkest
        },
      },

      fonts: {
        heading: { value: "Montserrat, sans-serif" },
        body: { value: "Montserrat, sans-serif" },
        mono: { value: "Roboto mono, monospace" },
      },
    },
    semanticTokens: {
      colors: {
        background: {
          value: {
            base: "{colors.gray.50}",
            _dark: "{colors.gray.900}",
          },
        },
        text: {
          value: {
            base: "{colors.gray.900}",
            _dark: "{colors.gray.100}",
          },
        },

        primary: {
          solid: {
            value: {
              base: "{colors.airForceBlue.500}",
              _dark: "{colors.airForceBlue.500}",
            },
          },
          contrast: {
            value: {
              base: "{colors.airForceBlue.100}",
              _dark: "{colors.airForceBlue.900}",
            },
          },
          fg: {
            value: {
              base: "{colors.airForceBlue.700}",
              _dark: "{colors.airForceBlue.300}",
            },
          },
          muted: {
            value: {
              base: "{colors.airForceBlue.100}",
              _dark: "{colors.airForceBlue.900}",
            },
          },
          subtle: {
            value: {
              base: "{colors.airForceBlue.200}",
              _dark: "{colors.airForceBlue.800}",
            },
          },
          emphasized: {
            value: {
              base: "{colors.airForceBlue.300}",
              _dark: "{colors.airForceBlue.700}",
            },
          },
          focusRing: {
            value: {
              base: "{colors.airForceBlue.400}",
              _dark: "{colors.airForceBlue.600}",
            },
          },
        },

        accent: {
          solid: {
            value: {
              base: "{colors.deepPlum.900}",
              _dark: "{colors.deepPlum.100}",
            },
          },
          contrast: {
            value: {
              base: "{colors.deepPlum.100}",
              _dark: "{colors.deepPlum.900}",
            },
          },
          fg: {
            value: {
              base: "{colors.deepPlum.700}",
              _dark: "{colors.deepPlum.200}",
            },
          },
          muted: {
            value: {
              base: "{colors.deepPlum.100}",
              _dark: "{colors.deepPlum.900}",
            },
          },
          subtle: {
            value: {
              base: "{colors.deepPlum.200}",
              _dark: "{colors.deepPlum.700}",
            },
          },
          emphasized: {
            value: {
              base: "{colors.deepPlum.300}",
              _dark: "{colors.deepPlum.600}",
            },
          },
          focusRing: {
            value: {
              base: "{colors.deepPlum.500}",
              _dark: "{colors.deepPlum.500}",
            },
          },
        },

        // Palettes for message callouts
        observing: {
          solid: {
            value: {
              base: "{colors.warmNeutral.900}",
              _dark: "{colors.warmNeutral.100}",
            },
          },
          contrast: {
            value: {
              base: "{colors.warmNeutral.100}",
              _dark: "{colors.warmNeutral.900}",
            },
          },
          fg: {
            value: {
              base: "{colors.warmNeutral.700}",
              _dark: "{colors.warmNeutral.200}",
            },
          },
          muted: {
            value: {
              base: "{colors.warmNeutral.100}",
              _dark: "{colors.warmNeutral.900}",
            },
          },
          subtle: {
            value: {
              base: "{colors.warmNeutral.200}",
              _dark: "{colors.warmNeutral.700}",
            },
          },
          emphasized: {
            value: {
              base: "{colors.warmNeutral.300}",
              _dark: "{colors.warmNeutral.600}",
            },
          },
          focusRing: {
            value: {
              base: "{colors.warmNeutral.500}",
              _dark: "{colors.warmNeutral.500}",
            },
          },
        },
        thinking: {
          solid: {
            value: {
              base: "{colors.deepPlum.800}",
              _dark: "{colors.deepPlum.200}",
            },
          },
          contrast: {
            value: {
              base: "{colors.deepPlum.200}",
              _dark: "{colors.deepPlum.800}",
            },
          },
          fg: {
            value: {
              base: "{colors.deepPlum.600}",
              _dark: "{colors.deepPlum.300}",
            },
          },
          muted: {
            value: {
              base: "{colors.deepPlum.200}",
              _dark: "{colors.deepPlum.700}",
            },
          },
          subtle: {
            value: {
              base: "{colors.deepPlum.300}",
              _dark: "{colors.deepPlum.600}",
            },
          },
          emphasized: {
            value: {
              base: "{colors.deepPlum.400}",
              _dark: "{colors.deepPlum.500}",
            },
          },
          focusRing: {
            value: {
              base: "{colors.deepPlum.500}",
              _dark: "{colors.deepPlum.500}",
            },
          },
        },

        insightful: {
          solid: {
            value: {
              base: "{colors.neutralGreen.900}",
              _dark: "{colors.neutralGreen.100}",
            },
          },
          contrast: {
            value: {
              base: "{colors.neutralGreen.100}",
              _dark: "{colors.neutralGreen.900}",
            },
          },
          fg: {
            value: {
              base: "{colors.neutralGreen.700}",
              _dark: "{colors.neutralGreen.200}",
            },
          },
          muted: {
            value: {
              base: "{colors.neutralGreen.100}",
              _dark: "{colors.neutralGreen.900}",
            },
          },
          subtle: {
            value: {
              base: "{colors.neutralGreen.200}",
              _dark: "{colors.neutralGreen.700}",
            },
          },
          emphasized: {
            value: {
              base: "{colors.neutralGreen.300}",
              _dark: "{colors.neutralGreen.600}",
            },
          },
          focusRing: {
            value: {
              base: "{colors.neutralGreen.500}",
              _dark: "{colors.neutralGreen.500}",
            },
          },
        },
      },
    },
  },
});

export const system = createSystem(defaultConfig, config);
