# CI/CD Documentation

This directory contains GitHub Actions workflows and configuration for automated testing, building, and deployment of the Word Filter Application.

## Workflows

### 🔄 Main CI/CD Pipeline (`ci-cd.yml`)
Runs on push to `main` and `develop` branches and all pull requests.

**Jobs:**
- **Backend Tests**: Python/FastAPI testing with pytest and coverage
- **Frontend Tests**: Angular testing with Karma/Jasmine
- **Build**: Build both applications and create artifacts
- **Docker Build**: Build and push Docker images (main branch only)
- **Integration Tests**: End-to-end testing between frontend and backend
- **Security Scan**: Vulnerability scanning with Trivy
- **Deploy**: Production deployment (main branch only)

### 🚀 Release Pipeline (`release.yml`)
Triggers on version tags (`v*`) to create GitHub releases.

**Features:**
- Automatic changelog generation
- Build and upload release artifacts
- Tag and push Docker images with version numbers
- Create GitHub releases with download links

### 🔍 PR Checks (`pr-check.yml`)
Runs on pull requests for quick validation.

**Checks:**
- PR title format validation (conventional commits)
- Code linting and formatting
- Security scanning
- Dependency vulnerability checks
- Automated PR commenting with results

## Dependencies Management

### 🤖 Dependabot (`dependabot.yml`)
Automatically creates PRs for dependency updates:
- **Python packages** (backend): Weekly on Mondays
- **npm packages** (frontend): Weekly on Mondays  
- **Docker base images**: Weekly on Tuesdays
- **GitHub Actions**: Monthly updates

## Issue & PR Templates

### Issue Templates
- **Bug Report**: Structured bug reporting with environment details
- **Feature Request**: Feature suggestions with priority and implementation ideas
- **Question**: General questions about the project

### Pull Request Template
- Checklist for PR requirements
- Component impact assessment
- Testing verification
- Related issues linking

## Environment Setup

### Required Secrets
Add these secrets to your GitHub repository:

```bash
# Docker Hub (for image publishing)
DOCKER_USERNAME=your-docker-username
DOCKER_TOKEN=your-docker-access-token

# Optional: Add deployment secrets
# AWS_ACCESS_KEY_ID=your-aws-key
# AWS_SECRET_ACCESS_KEY=your-aws-secret
# KUBE_CONFIG=your-kubernetes-config
```

### Environments
Configure environments in GitHub Settings:
- **production**: Requires manual approval for deployments

## Workflow Triggers

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci-cd.yml` | Push to main/develop, PRs | Main testing and deployment |
| `release.yml` | Tags matching `v*` | Create releases and publish |
| `pr-check.yml` | Pull requests | Quick validation and feedback |

## Badge Status

Add these badges to your README.md:

```markdown
[![CI/CD](https://github.com/phanivikranth/word-filter-app/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/phanivikranth/word-filter-app/actions/workflows/ci-cd.yml)
[![Release](https://github.com/phanivikranth/word-filter-app/actions/workflows/release.yml/badge.svg)](https://github.com/phanivikranth/word-filter-app/actions/workflows/release.yml)
```

## Development Workflow

1. **Create Feature Branch**: `git checkout -b feature/my-feature`
2. **Make Changes**: Implement your feature with tests
3. **Push Changes**: `git push origin feature/my-feature`
4. **Create PR**: GitHub will automatically run PR checks
5. **Review & Merge**: After approval and checks pass
6. **Release**: Create a tag (`git tag v1.1.0`) to trigger release

## Local Development

### Pre-commit Setup
Install pre-commit hooks for local validation:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks (from project root)
pre-commit install

# Run manually
pre-commit run --all-files
```

### Testing Locally
```bash
# Backend tests
cd backend
python -m pytest tests/ -v --cov

# Frontend tests  
cd frontend
npm test

# Integration tests
# Start backend first, then run frontend integration tests
```

## Monitoring & Alerts

- **GitHub Actions**: Monitor workflow status in Actions tab
- **Dependabot**: Check dependency update PRs weekly
- **Security Alerts**: Review Dependabot security advisories
- **Release Notes**: Auto-generated from git commits

## Troubleshooting

### Common Issues

1. **Docker Push Fails**: Check DOCKER_TOKEN secret is valid
2. **Tests Timeout**: Increase timeout in workflow files
3. **Linting Fails**: Run `black .` and `isort .` in backend, `npm run lint -- --fix` in frontend
4. **Release Creation Fails**: Ensure tag follows `v*` format (e.g., `v1.0.0`)

### Logs & Debugging

- Check workflow logs in GitHub Actions tab
- Use `actions/upload-artifact` to save debug files
- Enable debug logging with `ACTIONS_RUNNER_DEBUG=true` secret

## Contributing

1. Follow conventional commit format for PR titles
2. Add tests for new features
3. Update documentation as needed
4. Ensure all CI checks pass
5. Request review from maintainers
