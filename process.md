# Project Process and Structure

This document outlines the development process, project structure, and key architectural patterns used in this project.

## 1. Docker for Development

The entire development environment is containerized using Docker and managed via `docker-compose.yml`. This ensures consistency across different developer machines.

The main services are:
- `db`: A PostgreSQL database with the `pgvector` extension for vector similarity search.
- `db-seed`: A service to seed the database with initial data.
- `api`: The Python-based backend server (FastAPI).
- `bot`: A Telegram bot service.
- `frontend`: The Next.js frontend application.

To start all services, run:
```bash
docker-compose up -d
```

The backend API will be available at `http://localhost:8000` and the frontend at `http://localhost:3009`.

### Backend Dependencies
Backend Python dependencies are managed by `pip` and defined in `requirements.txt`. The `Dockerfile` installs these dependencies when building the `api` image.

### Frontend Dependencies
Frontend JavaScript/TypeScript dependencies are managed by `npm` (or `yarn`/`pnpm`) and defined in `frontend/package.json`. The `frontend/Dockerfile` handles the installation of these dependencies.

## 2. Frontend Feature Structure

The frontend code, located in `frontend/src`, is organized by features. This is a common and effective pattern for scaling frontend applications.

The current feature structure is:
```
frontend/src/features/
├── messages/
├── organizations/
├── problems/
├── process-message/
├── projects/
└── solutions/
```

### Recommended Patterns for Features

For each feature directory (e.g., `problems`), we recommend the following structure:
- **`components/`**: Contains React components specific to this feature.
- **`hooks/`**: Custom React hooks for the feature's logic.
- **`services/`**: Functions for making API calls related to the feature.
- **`types/`**: TypeScript type definitions for the feature's data structures.

This structure promotes modularity, making it easier to find, update, and reuse code related to a specific feature.

## 3. Server API Endpoints

The backend server provides a RESTful API for managing the application's data. The available endpoints are defined in `server/main.py`.

### Main Endpoints
- `POST /process-message`: Processes a raw text message, detects problems, finds solutions, and returns a structured response.

### CRUD Endpoints

The API provides full CRUD (Create, Read, Update, Delete) operations for the following resources:

- **Projects**: `GET /projects`, `POST /projects`, `GET /projects/{id}`, `PUT /projects/{id}`, `DELETE /projects/{id}`
- **Problems**: `GET /problems`, `POST /problems`, `GET /problems/{id}`, `PUT /problems/{id}`, `DELETE /problems/{id}`
- **Solutions**: `GET /solutions`, `POST /solutions`, `GET /solutions/{id}`, `PUT /solutions/{id}`, `DELETE /solutions/{id}`
- **Organizations**: `GET /organizations`, `POST /organizations`, `GET /organizations/{id}`, `PUT /organizations/{id}`, `DELETE /organizations/{id}`
- **Messages**: `GET /messages`, `GET /messages/{id}`

A command-line interface (`cli.py`) is also available to interact with these endpoints.

## 4. Context7 Usage

This project utilizes `context7` to retrieve up-to-date documentation and code examples for various libraries. It is crucial to use the tooling provided to ensure that we are referencing the correct versions of libraries and following best practices. Adherence to the information provided by `context7` will help maintain code quality and reduce integration issues.

## 5. UI Components and Theming

The frontend uses `shadcn/ui` for its component library, which provides a set of accessible and customizable components built on top of Radix UI and Tailwind CSS.

### Configuration
- **Style:** `new-york`
- **Base Color:** `slate`
- **CSS Variables:** Enabled
- **Components Alias:** `@/components`
- **Utils Alias:** `@/lib/utils`

New components can be added using the `shadcn-ui` CLI.

### Theming

Theming is managed through CSS variables as defined in `src/app/globals.css`, following the `shadcn/ui` theming guide. The base color is `slate`, but this can be customized. When adding new components or custom styles, prefer using the defined Tailwind CSS theme and color variables to maintain a consistent look and feel.

### Component Decomposition

When building new UI features, components should be decomposed into smaller, reusable pieces.

- **Atomic Components:** Basic UI elements (e.g., `Button`, `Input`, `Card`) are located in `src/components/ui`. These are typically the base components provided by `shadcn/ui`.
- **Feature Components:** Components that are specific to a feature (e.g., `ProblemList`, `ProjectForm`) should be located within the `components` directory of that feature (e.g., `src/features/problems/components/`).
- **Layout Components:** Components that define the overall page structure (e.g., `Header`, `Sidebar`, `PageLayout`) should be placed in `src/components/layout/`.

This decomposition strategy helps in creating a scalable and maintainable component architecture.

## 6. Data Access Patterns

The frontend uses a combination of React Hooks and service layers to manage data fetching, caching, and state management.

### Service Layer
- **Purpose:** The service layer is responsible for all communication with the backend API. It abstracts the details of the HTTP requests, making the rest of the application unaware of the specific API endpoints or data transport mechanisms.
- **Location:** Each feature has its own `services` directory (e.g., `frontend/src/features/problems/services/api.ts`).
- **Implementation:** Service files export async functions that perform API calls (e.g., `getProblems`, `createProblem`). These functions handle the request and response, throwing an error if the request fails.

### Custom Hooks
- **Purpose:** Custom hooks are used to encapsulate and manage the state and logic related to data fetching within React components. They utilize the service layer to fetch data and manage loading and error states.
- **Location:** Each feature has its own `hooks` directory (e.g., `frontend/src/features/problems/hooks/useProblems.ts`).
- **Implementation:** A typical data-fetching hook (e.g., `useProblems`) will use the `useState` and `useEffect` hooks to fetch data when the component mounts, and it will provide the component with the fetched data, a loading state, and any potential errors.

This pattern separates concerns effectively: services handle *how* to get data, and hooks handle *when* to get it and what to do with it, allowing components to remain clean and focused on rendering the UI.