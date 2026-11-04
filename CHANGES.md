# Changes (professor's new instructions)
1. Landing page: "See what it looks like inside" section with real screenshots (static/img/).
2. Side panel on every signed-in page (templates/base.html); Analysis & charts has section links.
3. Month-wise categories (month_categories.py, /categories): Core / Occasional priority from earlier months, delete a suggestion per month.
4. CSV download by last 1 month, 3 months, custom months, or all (templates/_export_form.html).
5. Adding a Salary opens an advised budget per category (analysis.salary_budget_plan, /budgets).
Deploy: just push to GitHub. The new table `month_categories` is created automatically on first login (also added to schema.sql).
