module.exports = {
  "src/neuron_client/src/**/*.{ts,tsx}": [
    "npm run lint -- --fix"
  ],
  "src/neuron_client/src/**/*.{js,jsx}": [
    "npm run lint -- --fix"
  ],
  "src/neuron_server/**/*.py": [
    "poetry run ruff check --fix"
  ]
};