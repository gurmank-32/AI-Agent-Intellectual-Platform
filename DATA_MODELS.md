# Compliance Agent — Data Models

## Supabase Tables

### jurisdictions
| Column      | Type    | Notes                              |
|-------------|---------|-------------------------------------|
| id          | SERIAL  | Primary key                         |
| type        | TEXT    | federal / state / county / city     |
| name        | TEXT    | e.g. "California", "Los Angeles"    |
| parent_id   | INT     | FK → jurisdictions.id (nullable)    |
| state_code  | CHAR(2) | e.g. "CA", "TX"                     |
| fips_code   | TEXT    | For geocoding lookups (nullable)    |

### regulations
| Column          | Type        | Notes                           |
|-----------------|-------------|----------------------------------|
| id              | SERIAL      | Primary key                      |
| jurisdiction_id | INT         | FK → jurisdictions.id            |
| domain          | TEXT        | housing / pet / insurance        |
| category        | TEXT        | e.g. "ESA", "Rent Control"       |
| source_name     | TEXT        |                                  |
| url             | TEXT        |                                  |
| content         | TEXT        | Full scraped text                |
| content_hash    | TEXT        | SHA256 for change detection      |
| version         | INT         | Increments on each change        |
| is_current      | BOOL        | Only latest version = true       |
| effective_date  | DATE        | Nullable                         |
| created_at      | TIMESTAMPTZ | auto                             |

### regulation_embeddings
| Column        | Type          | Notes                    |
|---------------|---------------|--------------------------|
| id            | SERIAL        | Primary key              |
| regulation_id | INT           | FK → regulations.id      |
| embedding     | vector(1536)  | pgvector                 |
| chunk_text    | TEXT          | 800-char chunk           |

### email_subscriptions
| Column        | Type        | Notes                         |
|---------------|-------------|-------------------------------|
| id            | SERIAL      | Primary key                   |
| email         | TEXT        |                               |
| jurisdiction_id | INT       | FK → jurisdictions.id         |
| subscribed_at | TIMESTAMPTZ | auto                          |
| is_active     | BOOL        | default true                  |

### regulation_updates
| Column               | Type        | Notes                      |
|----------------------|-------------|----------------------------|
| id                   | SERIAL      | Primary key                |
| regulation_id        | INT         | FK → regulations.id        |
| update_summary       | TEXT        |                            |
| affected_jurisdictions | JSONB     | list of jurisdiction ids   |
| detected_at          | TIMESTAMPTZ | auto                       |

### pet_policies
| Column                  | Type    | Notes                           |
|-------------------------|---------|----------------------------------|
| id                      | SERIAL  | Primary key                      |
| jurisdiction_id         | INT     | FK → jurisdictions.id            |
| esa_deposit_allowed     | BOOL    | Always false at federal level    |
| service_animal_fee      | BOOL    | Always false at federal level    |
| breed_restrictions      | JSONB   | list of restricted breed names   |
| max_pet_deposit_amount  | NUMERIC | Nullable — state sets this       |
| source_regulation_id    | INT     | FK → regulations.id              |

### insurance_requirements
| Column                   | Type    | Notes                     |
|--------------------------|---------|---------------------------|
| id                       | SERIAL  | Primary key               |
| jurisdiction_id          | INT     | FK → jurisdictions.id     |
| landlord_can_require     | BOOL    |                           |
| min_liability_coverage   | NUMERIC | Nullable                  |
| tenant_must_show_proof   | BOOL    |                           |
| notes                    | TEXT    | Nullable                  |
| source_regulation_id     | INT     | FK → regulations.id       |

## Pydantic Models (db/models.py)
- Jurisdiction, Regulation, RegulationEmbedding
- EmailSubscription, RegulationUpdate
- PetPolicy, InsuranceRequirement
- ComplianceResult, ComplianceIssue (core/compliance/checker.py)
- UpdateResult (core/regulations/update_checker.py)
- SearchResult (core/rag/vector_store.py)