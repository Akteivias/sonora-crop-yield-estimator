# Project Scope & Boundaries

- This repository is a personal **Machine Learning Zoomcamp 2026 Midterm Project** targeting the canonical **16-point rubric** (`projects/README.md`) with the smallest credible implementation.
- **Strictly Modules 1–6 (`01-intro`–`06-trees`)**: Do not propose or require deep learning (CNNs, TensorFlow/Keras/PyTorch), serverless deployment (AWS Lambda/API Gateway), Kubernetes, TensorFlow Serving, KServe, or other Modules 8–10 / capstone infrastructure.
- **Originality**: The project must be original. Never reuse completed homework projects or their assets, previous-course projects, prior-cohort projects, or copied student work.
- **Disallowed datasets (`projects/README.md`)**: Do not use Car price prediction, Customer/Telco churn, Credit risk scoring, or Clothing classification.

# Undecided Choices & Tooling Policy

- Keep the **dataset, task type, specific baseline configuration, specific tree-based model, API framework, package manager, cloud provider, and directory layout** undecided until the project is chosen.
- Treat any local Module 5 pattern (such as FastAPI, `uv`, and Docker) as a reusable example, not a mandatory technology choice.
- Explain any non-obvious libraries or tools clearly in `README.md` so peer reviewers can understand and run the project without guessing.
- Exclude `GET /health`, pinned dependencies, lockfiles, cross-validation, three-or-more models, teardown notes, Gradio, and Streamlit from mandatory core requirements unless explicitly selected later. Gradio/Streamlit may never replace the HTTP API and Docker container.

# Modules 1–6 Workflow

1. **`01-intro` (Problem Framing)**: Frame one original prediction problem, its target user, decision/use case, and an accessible data source.
2. **`02-regression` / `03-classification` (Task & Baseline)**: Select one appropriate supervised task and establish a linear-regression or logistic-regression baseline model.
3. **`04-evaluation` (Evaluation)**: Select a suitable evaluation metric and a clear validation approach.
4. **`05-deployment` (Serving & Deployment)**: Export training to `train.py` saving the final deployable model artifact, serve predictions through an HTTP API, containerize with a production `Dockerfile`, and provide cloud-deployment code/instructions plus live URL or screenshot/video evidence.
5. **`06-trees` (Tree Candidate & Selection)**: Compare the baseline against a tuned tree-based candidate using the selected metric and document the final model selection rationale.

# Rubric Guardrails (16/16 Minimums)

- **Problem description (2 pts)**: `README.md` must clearly describe the problem, target user/decision, and how the model will be used.
- **EDA (2 pts)**: The notebook must include value ranges/distributions, missingness checks, target variable analysis, and feature importance (or task-appropriate equivalent).
- **Model training (3 pts)**: Train a linear-regression or logistic-regression baseline, plus a tuned tree-based candidate; compare them on the selected metric and document why the final model was selected.
- **Exporting notebook to script (1 pt)**: Export final training logic into a runnable `train.py` that trains and saves the deployable model artifact.
- **Reproducibility (1 pt)**: Commit the dataset (if practical) or provide exact download/retrieval instructions; both the notebook and `train.py` must run end-to-end without errors.
- **Model deployment (1 pt)**: Provide a runnable HTTP prediction service loading the saved artifact, with a documented request/response example in `README.md`.
- **Dependency & environment management (2 pts)**: Provide a dependency definition file plus `README.md` instructions for virtual-environment setup and activation.
- **Containerization (2 pts)**: Provide a production `Dockerfile` that builds and runs the prediction service, plus `docker build` and `docker run` instructions in `README.md`.
- **Cloud deployment (2 pts)**: Provide cloud deployment code/instructions plus a live testing URL or screenshot/video evidence of successful interaction with the deployed service.

# Containers & Optional Dev Environment

- **Production `Dockerfile` is mandatory**: It must build and run the HTTP prediction service and must not be replaced by Dev Container tooling.
- **Dev Containers are optional**: `.devcontainer/devcontainer.json` is permitted only as optional developer-convenience and reproducibility tooling. It is not a scored deliverable and must not replace standard setup instructions, Docker build/run verification, or a peer reviewer's ability to run the project without Dev Containers.
- **Minimalism & security**: If Dev Container support is added, keep it minimal and reuse the project `Dockerfile` where practical. Never enable privileged mode (`privileged: true` / `--privileged`), Docker-socket access (`/var/run/docker.sock`), host networking, or additional host mounts unless a documented project need requires them—these weaken isolation, and Docker-socket access effectively grants control over the host Docker daemon.

# Verification & Submission Hygiene

- Verify from a fresh clone that data retrieval/loading, the notebook, `train.py`, the HTTP prediction request, and `docker build` / `docker run` all succeed without errors (broken code or a broken `Dockerfile` scores 0 for that criterion).
- Before submission, record the exact final commit hash for the submission form and complete the 3 required peer reviews.
