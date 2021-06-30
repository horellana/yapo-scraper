create table sales (id uuid DEFAULT uuid_generate_v4(), title text not null, price real, url text not null, date timestamptz not null)

alter table sales add constraint sales_url_unique unique (sales);

alter table sales add constraint sales_url_unique unique (url);

alter table sales add constraint sales_url_unique unique (url);

alter table sales add column created_at timestampz not null default now();

alter table sales add column created_at timestamptz not null default now();

alter table sales add column deleted_at timestamptz;

create table search_terms (id uuid DEFAULT uuid_generate_v4(), name text not null, created_at timestamptz not null default now(), deleted_at timestamptz);

alter table search_terms add constraint search_terms_name_unique unique (name);

create table search_term_sales (
    id uuid not null default uuid_generate_v4(),
    search_term_id uuid not null,
    sale_id uuid not null,
    constraint fk_search_term foreign key (search_term_id) references search_terms(id),
    constraint fk_sale foreign key (sale_id) references sales(id)
);

alter table search_terms add constraint search_terms_id_unique unique (id);

create table search_term_sales (
    id uuid not null default uuid_generate_v4(),
    search_term_id uuid not null,
    sale_id uuid not null,
    constraint fk_search_term foreign key (search_term_id) references search_terms(id),
    constraint fk_sale foreign key (sale_id) references sales(id)
);

alter table search_term_sales add column created_at timestamptz not null default now();
alter table search_term_sales add column deleted_at timestamptz;

alter table sales add constraint sales_id_unique unique (id);

create table search_term_sales (
    id uuid not null default uuid_generate_v4(),
    search_term_id uuid not null,
    sale_id uuid not null,
    constraint fk_search_term foreign key (search_term_id) references search_terms(id),
    constraint fk_sale foreign key (sale_id) references sales(id)
);


alter table search_term_sales add unique (search_term_id, sale_id);

alter table search_term_sales add column created_at timestamptz not null default now();
alter table search_term_sales add column deleted_at timestamptz;

create table telegram_chats (
       id int not null primary key,
);

create table telegram_commands (
       id int not null primary key,
       telegram_chat_id int not null,

       command text not null,
       args text not null,

       constraint telegram_chat_fk
		  foreign key (telegram_chat_id) references telegram_chats(id)

);
