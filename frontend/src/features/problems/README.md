# Problems Feature

This feature module contains all the components and logic related to managing problems in the application.

## Structure

-   **components**: Contains React components specific to the problems feature.
-   **services**: Houses the functions for making API requests to the backend for problem-related operations.
-   **types**: Defines TypeScript types and interfaces for the problem data models.

## Pages

-   `app/problems/page.tsx`: Displays a list of all problems.
-   `app/problems/new/page.tsx`: A form to create a new problem.
-   `app/problems/[id]/page.tsx`: Displays the details of a single problem.
-   `app/problems/[id]/edit/page.tsx`: A form to edit an existing problem.