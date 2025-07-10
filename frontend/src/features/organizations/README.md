# Organizations Feature

This feature module contains all the components and logic related to managing organizations in the application.

## Structure

-   **components**: Contains React components specific to the organizations feature.
-   **services**: Houses the functions for making API requests to the backend for organization-related operations.
-   **types**: Defines TypeScript types and interfaces for the organization data models.

## Pages

-   `app/organizations/page.tsx`: Displays a list of all organizations.
-   `app/organizations/new/page.tsx`: A form to create a new organization.
-   `app/organizations/[id]/page.tsx`: Displays the details of a single organization.
-   `app/organizations/[id]/edit/page.tsx`: A form to edit an existing organization.