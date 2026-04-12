/**
 * Beep Graph logo — lambda with tilted ThugLife pixel glasses.
 */

import type { SVGProps } from "react";

export function BeepGraphLogo(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      {...props}
    >
      {/* Lambda body */}
      <path
        d="M6 20l6.5 -9"
        stroke="currentColor"
        strokeWidth="2.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M19 20c-6 0 -6 -16 -12 -16"
        stroke="currentColor"
        strokeWidth="2.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* ThugLife pixel glasses — tilted, at intersection */}
      <g transform="translate(5.4, 9.5) scale(0.52) rotate(8 12.5 2.5)">
        <path
          fill="#fafafa"
          d="m0,0v2h1v1h1v1h1v1h7v-1h1v-1h1v-2h2v2h1v1h1v1h6v-1h1v-1h1v-1h1v-2z"
        />
        <path
          fill="#09090b"
          d="m2,1v1h4v2h1v-1h-2v-2h-1v3h1v-1h-2v-2z"
        />
        <path
          fill="#09090b"
          d="m15,1v1h4v2h1v-1h-2v-2h-1v3h1v-1h-2v-2z"
        />
      </g>
    </svg>
  );
}
