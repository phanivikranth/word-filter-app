/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./src/**/*.{html,ts}",
  ],
  theme: {
    extend: {
      colors: {
        "inverse-on-surface": "var(--inverse-on-surface)",
        "primary": "var(--primary)",
        "tertiary-container": "var(--tertiary-container)",
        "on-tertiary": "var(--on-tertiary)",
        "tertiary": "var(--tertiary)",
        "on-primary-fixed-variant": "var(--on-primary-fixed-variant)",
        "surface-container-high": "var(--surface-container-high)",
        "primary-fixed-dim": "var(--primary-fixed-dim)",
        "surface-variant": "var(--surface-variant)",
        "surface-container-lowest": "var(--surface-container-lowest)",
        "on-tertiary-fixed-variant": "var(--on-tertiary-fixed-variant)",
        "on-background": "var(--on-background)",
        "on-surface-variant": "var(--on-surface-variant)",
        "primary-fixed": "var(--primary-fixed)",
        "surface-tint": "var(--surface-tint)",
        "outline-variant": "var(--outline-variant)",
        "inverse-primary": "var(--inverse-primary)",
        "primary-container": "var(--primary-container)",
        "outline": "var(--outline)",
        "background": "var(--background)",
        "surface-container": "var(--surface-container)",
        "on-surface": "var(--on-surface)",
        "surface-container-highest": "var(--surface-container-highest)",
        "error-container": "var(--error-container)",
        "error": "var(--error)",
        "tertiary-fixed": "var(--tertiary-fixed)",
        "on-secondary-container": "var(--on-secondary-container)",
        "on-secondary-fixed": "var(--on-secondary-fixed)",
        "secondary-fixed": "var(--secondary-fixed)",
        "on-secondary": "var(--on-secondary)",
        "on-error-container": "var(--on-error-container)",
        "surface-container-low": "var(--surface-container-low)",
        "secondary-container": "var(--secondary-container)",
        "on-error": "var(--on-error)",
        "on-primary": "var(--on-primary)",
        "surface-dim": "var(--surface-dim)",
        "tertiary-fixed-dim": "var(--tertiary-fixed-dim)",
        "surface-bright": "var(--surface-bright)",
        "secondary": "var(--secondary)",
        "inverse-surface": "var(--inverse-surface)",
        "on-tertiary-container": "var(--on-tertiary-container)",
        "on-secondary-fixed-variant": "var(--on-secondary-fixed-variant)",
        "on-primary-fixed": "var(--on-primary-fixed)",
        "surface": "var(--surface)",
        "on-tertiary-fixed": "var(--on-tertiary-fixed)",
        "secondary-fixed-dim": "var(--secondary-fixed-dim)",
        "on-primary-container": "var(--on-primary-container)"
      },
      borderRadius: {
        "DEFAULT": "0.75rem",
        "lg": "0.75rem",
        "xl": "1rem",
        "full": "9999px"
      },
      spacing: {
        "sm": "12px",
        "lg": "48px",
        "md": "24px",
        "gutter": "24px",
        "base": "8px",
        "xs": "4px",
        "xl": "80px",
        "container-max": "1360px"
      },
      fontFamily: {
        "display-lg": ["Plus Jakarta Sans", "sans-serif"],
        "label-md": ["Plus Jakarta Sans", "sans-serif"],
        "headline-lg-mobile": ["Plus Jakarta Sans", "sans-serif"],
        "label-sm": ["Plus Jakarta Sans", "sans-serif"],
        "body-md": ["Plus Jakarta Sans", "sans-serif"],
        "headline-md": ["Plus Jakarta Sans", "sans-serif"],
        "headline-lg": ["Plus Jakarta Sans", "sans-serif"],
        "body-lg": ["Plus Jakarta Sans", "sans-serif"]
      },
      fontSize: {
        "display-lg": [
          "48px",
          {
            "lineHeight": "56px",
            "letterSpacing": "-0.02em",
            "fontWeight": "800"
          }
        ],
        "label-md": [
          "14px",
          {
            "lineHeight": "20px",
            "letterSpacing": "0.01em",
            "fontWeight": "600"
          }
        ],
        "headline-lg-mobile": [
          "28px",
          {
            "lineHeight": "36px",
            "fontWeight": "700"
          }
        ],
        "label-sm": [
          "12px",
          {
            "lineHeight": "16px",
            "letterSpacing": "0.03em",
            "fontWeight": "700"
          }
        ],
        "body-md": [
          "16px",
          {
            "lineHeight": "24px",
            "fontWeight": "400"
          }
        ],
        "headline-md": [
          "24px",
          {
            "lineHeight": "32px",
            "fontWeight": "600"
          }
        ],
        "headline-lg": [
          "32px",
          {
            "lineHeight": "40px",
            "fontWeight": "700"
          }
        ],
        "body-lg": [
          "18px",
          {
            "lineHeight": "28px",
            "fontWeight": "600"
          }
        ],
        "headline-sm": [
          "18px",
          {
            "lineHeight": "26px",
            "fontWeight": "600"
          }
        ]
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
