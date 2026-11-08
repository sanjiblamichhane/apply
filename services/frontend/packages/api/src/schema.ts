/* eslint-disable */
// Generated from services/backend/openapi.json by scripts/generate.mjs. Don't edit: regenerate.

export interface paths {
    "/api/v1/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Health
         * @description Liveness, and whether the database and the file bucket answer.
         */
        get: operations["health_api_v1_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/system/model": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Model Status
         * @description Is the model reachable, and are the configured models pulled?
         */
        get: operations["model_status_api_v1_system_model_get"];
        /**
         * Choose Model
         * @description Use a model found on this machine, after a short test: a server and model just found, and a usable JSON
         *     answer from each chosen model. MODEL_NOT_FOUND or MODEL_TEST_FAILED otherwise, and nothing changes.
         */
        put: operations["choose_model_api_v1_system_model_put"];
        post?: never;
        /**
         * Reset Model
         * @description Back to the settings' model (.env).
         */
        delete: operations["reset_model_api_v1_system_model_delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/system/models": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Models
         * @description The model servers on this machine (the configured host, fixed ports), their models, and which is in use.
         */
        get: operations["models_api_v1_system_models_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/sign-in": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Sign In */
        post: operations["sign_in_api_v1_auth_sign_in_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/setup": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Setup
         * @description Whether "Create an account" is offered: on the first run (the owner's), then while the owner keeps
         *     registration open. Never with web setup off (accounts are made with `apply init`).
         */
        get: operations["setup_api_v1_auth_setup_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/register": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Register
         * @description Make an account and sign in: the owner's on the first run, anyone's after that while registration is open
         *     (403 REGISTRATION_CLOSED otherwise; 409 EMAIL_TAKEN). Web setup off: `apply init` only.
         */
        post: operations["register_api_v1_auth_register_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/forgot-password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Forgot Password
         * @description Email a link to choose a new password, if there's an account with this email. The answer is the same
         *     whether or not there is (202), and the email is sent after it. 409 MAIL_NOT_SET_UP with no SMTP server.
         */
        post: operations["forgot_password_api_v1_auth_forgot_password_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/reset-password/check": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Check Reset
         * @description The account a reset link is for, while it works (404 RESET_LINK_INVALID once used or expired).
         */
        post: operations["check_reset_api_v1_auth_reset_password_check_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/reset-password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Reset Password
         * @description A new password from a reset link. Every session of the account ends, so the person signs in again; the
         *     link and any other of the account's stop working.
         */
        post: operations["reset_password_api_v1_auth_reset_password_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/system/registration": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Registration */
        get: operations["get_registration_api_v1_system_registration_get"];
        /**
         * Set Registration
         * @description Open or close "Create an account" on the sign-in page. Existing accounts are untouched.
         */
        put: operations["set_registration_api_v1_system_registration_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/people": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List People
         * @description Every account on this apply (never what's in them).
         */
        get: operations["list_people_api_v1_people_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/people/{person_id}/disable": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Disable Person */
        post: operations["disable_person_api_v1_people__person_id__disable_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/people/{person_id}/enable": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Enable Person */
        post: operations["enable_person_api_v1_people__person_id__enable_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/people/{person_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /**
         * Delete Person
         * @description The account and everything in it, its files in the bucket too. The owner's own can't be deleted.
         */
        delete: operations["delete_person_api_v1_people__person_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/sign-out": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Sign Out */
        post: operations["sign_out_api_v1_auth_sign_out_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Me */
        get: operations["me_api_v1_auth_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Update Me
         * @description The account's language (the web app also keeps it in a cookie, for before sign-in).
         */
        patch: operations["update_me_api_v1_auth_me_patch"];
        trace?: never;
    };
    "/api/v1/packs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Packs */
        get: operations["list_packs_api_v1_packs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/packs/{key}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Pack */
        get: operations["get_pack_api_v1_packs__key__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/profiles": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Profiles */
        get: operations["list_profiles_api_v1_profiles_get"];
        put?: never;
        /** Create Profile */
        post: operations["create_profile_api_v1_profiles_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/profiles/{profile_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Profile */
        get: operations["get_profile_api_v1_profiles__profile_id__get"];
        put?: never;
        post?: never;
        /** Delete Profile */
        delete: operations["delete_profile_api_v1_profiles__profile_id__delete"];
        options?: never;
        head?: never;
        /** Update Profile */
        patch: operations["update_profile_api_v1_profiles__profile_id__patch"];
        trace?: never;
    };
    "/api/v1/profiles/import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Import Profile
         * @description A profile made from a document. 202 with the profile, saved at once; the model reads the document into its
         *     fields in the background (``reading.status`` pending → ready, or failed with a code). Poll it, then check
         *     every field. 422 UPLOAD_TOO_LARGE, UPLOAD_UNSUPPORTED, or UPLOAD_NO_TEXT (a scan with no text in it).
         */
        post: operations["import_profile_api_v1_profiles_import_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/profiles/{profile_id}/duplicate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Duplicate Profile
         * @description A copy of the profile to change what's different ("Name (copy)" unless named), never the default.
         */
        post: operations["duplicate_profile_api_v1_profiles__profile_id__duplicate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/profiles/{profile_id}/read": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Read Profile Again
         * @description Read the profile's document again; what's read replaces its fields. 409 PROFILE_NOT_READ without one.
         */
        post: operations["read_profile_again_api_v1_profiles__profile_id__read_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/profiles/{profile_id}/source": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Profile Source
         * @description The document the profile was made from. 409 PROFILE_NOT_READ without one.
         */
        get: operations["profile_source_api_v1_profiles__profile_id__source_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/opportunities": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Opportunities */
        get: operations["list_opportunities_api_v1_opportunities_get"];
        put?: never;
        /**
         * Paste Opportunity
         * @description Paste a link or the text. New: 201; the same link or text again: 200 with the existing one.
         */
        post: operations["paste_opportunity_api_v1_opportunities_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/opportunities/{opportunity_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Opportunity */
        get: operations["get_opportunity_api_v1_opportunities__opportunity_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Opportunity */
        patch: operations["update_opportunity_api_v1_opportunities__opportunity_id__patch"];
        trace?: never;
    };
    "/api/v1/opportunities/{opportunity_id}/extract": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Extract Opportunity
         * @description Have the model read the opportunity's text again.
         */
        post: operations["extract_opportunity_api_v1_opportunities__opportunity_id__extract_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/applications": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Applications */
        get: operations["list_applications_api_v1_applications_get"];
        put?: never;
        /** Create Application */
        post: operations["create_application_api_v1_applications_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/applications/by-url": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Application By Url
         * @description The opportunity (and application, if there is one) for a page: the form the extension is looking at.
         */
        get: operations["application_by_url_api_v1_applications_by_url_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/applications/{application_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Application */
        get: operations["get_application_api_v1_applications__application_id__get"];
        put?: never;
        post?: never;
        /**
         * Delete Application
         * @description The application and everything made for it; its posting stays. 409 while Auto is sending it.
         */
        delete: operations["delete_application_api_v1_applications__application_id__delete"];
        options?: never;
        head?: never;
        /** Update Application */
        patch: operations["update_application_api_v1_applications__application_id__patch"];
        trace?: never;
    };
    "/api/v1/applications/{application_id}/stage": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Move Application */
        post: operations["move_application_api_v1_applications__application_id__stage_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/applications/{application_id}/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Application History */
        get: operations["application_history_api_v1_applications__application_id__history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/applications/{application_id}/documents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Documents */
        get: operations["list_documents_api_v1_applications__application_id__documents_get"];
        put?: never;
        /**
         * Request Document
         * @description Write a document in the background. 202 with the pending document; poll it until it is ready or failed.
         */
        post: operations["request_document_api_v1_applications__application_id__documents_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/applications/{application_id}/documents/{document_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Document */
        get: operations["get_document_api_v1_applications__application_id__documents__document_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/source-kinds": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Source Kinds
         * @description Where postings can come from, what each needs, and what its terms ask of us.
         */
        get: operations["list_source_kinds_api_v1_source_kinds_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/sources": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Sources */
        get: operations["list_sources_api_v1_sources_get"];
        put?: never;
        /**
         * Create Source
         * @description Add a source; it's fetched straight away, then on its schedule.
         */
        post: operations["create_source_api_v1_sources_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/sources/recognise": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Recognise Source
         * @description Which kind of source a pasted address is (a company's job board page), and the config it stands for.
         */
        post: operations["recognise_source_api_v1_sources_recognise_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/sources/{source_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Source */
        get: operations["get_source_api_v1_sources__source_id__get"];
        put?: never;
        post?: never;
        /** Delete Source */
        delete: operations["delete_source_api_v1_sources__source_id__delete"];
        options?: never;
        head?: never;
        /** Update Source */
        patch: operations["update_source_api_v1_sources__source_id__patch"];
        trace?: never;
    };
    "/api/v1/sources/{source_id}/fetch": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Fetch Source
         * @description Fetch now (409 SOURCE_TOO_SOON within the interval the source's terms ask for).
         */
        post: operations["fetch_source_api_v1_sources__source_id__fetch_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/searches": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Searches */
        get: operations["list_searches_api_v1_searches_get"];
        put?: never;
        /**
         * Create Search
         * @description Save a search; it runs over what's already here straight away, then on every fetch.
         */
        post: operations["create_search_api_v1_searches_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/searches/{search_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Search */
        get: operations["get_search_api_v1_searches__search_id__get"];
        put?: never;
        post?: never;
        /** Delete Search */
        delete: operations["delete_search_api_v1_searches__search_id__delete"];
        options?: never;
        head?: never;
        /** Update Search */
        patch: operations["update_search_api_v1_searches__search_id__patch"];
        trace?: never;
    };
    "/api/v1/matches": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Matches
         * @description The inbox: best fit first (unscored last), then newest. Default: new and saved.
         */
        get: operations["list_matches_api_v1_matches_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/matches/{match_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Update Match
         * @description Save, dismiss, or put back (undo).
         */
        patch: operations["update_match_api_v1_matches__match_id__patch"];
        trace?: never;
    };
    "/api/v1/matches/{match_id}/track": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Track Match
         * @description Make it an application (or point it at the one already tracking this job).
         */
        post: operations["track_match_api_v1_matches__match_id__track_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/briefings/today": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Todays Briefing
         * @description Today's briefing, in the owner's time zone; built at their briefing hour (or POST to build it now).
         */
        get: operations["todays_briefing_api_v1_briefings_today_get"];
        put?: never;
        /** Build Todays Briefing */
        post: operations["build_todays_briefing_api_v1_briefings_today_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/applications/{application_id}/documents/{document_id}/content": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Edit Document
         * @description Your own wording: saved as a new version (the one in use) and checked again.
         */
        put: operations["edit_document_api_v1_applications__application_id__documents__document_id__content_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/applications/{application_id}/documents/{document_id}/warnings/{warning_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Resolve Warning
         * @description "It's true" (kept), or open again.
         */
        post: operations["resolve_warning_api_v1_applications__application_id__documents__document_id__warnings__warning_id__post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/applications/{application_id}/documents/{document_id}/review": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Mark Reviewed */
        post: operations["mark_reviewed_api_v1_applications__application_id__documents__document_id__review_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/applications/{application_id}/documents/{document_id}/check": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Check Document */
        post: operations["check_document_api_v1_applications__application_id__documents__document_id__check_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/applications/{application_id}/documents/{document_id}/pdf": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Document Pdf
         * @description The version in its template, printed to a tagged PDF/UA-1. 409 RENDER_PENDING (Retry-After) while it's made.
         */
        get: operations["document_pdf_api_v1_applications__application_id__documents__document_id__pdf_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/applications/{application_id}/documents/{document_id}/html": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Document Html
         * @description The version in its template, as the page (what's previewed). 409 RENDER_PENDING while it's made.
         */
        get: operations["document_html_api_v1_applications__application_id__documents__document_id__html_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/templates/{kind}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Template
         * @description The template your documents of this kind are made in (yours, or the default), and a sample in it.
         */
        get: operations["get_template_api_v1_templates__kind__get"];
        /**
         * Save Template
         * @description Your own template, kept if it passes every check (422 TEMPLATE_PROBLEMS with the problems if not).
         */
        put: operations["save_template_api_v1_templates__kind__put"];
        post?: never;
        /**
         * Reset Template
         * @description Back to the default.
         */
        delete: operations["reset_template_api_v1_templates__kind__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/templates/{kind}/default": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Default Template
         * @description The default, to start your own from.
         */
        get: operations["default_template_api_v1_templates__kind__default_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/templates/{kind}/check": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Check Template
         * @description What would stop this template being kept (nothing: it may be), and a sample in it, without keeping it.
         */
        post: operations["check_template_api_v1_templates__kind__check_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/answers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Answers */
        get: operations["list_answers_api_v1_answers_get"];
        put?: never;
        /** Create Answer */
        post: operations["create_answer_api_v1_answers_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/answers/defaults": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Add Default Answers
         * @description The pack's common questions you don't have yet (sensitive ones start as "Decline to answer").
         */
        post: operations["add_default_answers_api_v1_answers_defaults_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/answers/{answer_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Answer */
        delete: operations["delete_answer_api_v1_answers__answer_id__delete"];
        options?: never;
        head?: never;
        /** Update Answer */
        patch: operations["update_answer_api_v1_answers__answer_id__patch"];
        trace?: never;
    };
    "/api/v1/applications/{application_id}/kit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Application Kit
         * @description Everything to apply by hand: where, which documents (and their warnings), the answers.
         */
        get: operations["application_kit_api_v1_applications__application_id__kit_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/applications/{application_id}/submissions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Submit Application
         * @description "I've submitted it": what went out is recorded, and the application moves on. With a token, the channel is
         *     the token's (the extension), and the same submission again within the undo window is answered with the first.
         */
        post: operations["submit_application_api_v1_applications__application_id__submissions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/submissions/{submission_id}/undo": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Undo Submission
         * @description Undo, within 10 minutes (UNDO_TOO_LATE after).
         */
        post: operations["undo_submission_api_v1_submissions__submission_id__undo_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tokens": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Tokens */
        get: operations["list_tokens_api_v1_tokens_get"];
        put?: never;
        /**
         * Create Token
         * @description A token for the extension. Its secret is in this answer only: apply keeps a hash.
         */
        post: operations["create_token_api_v1_tokens_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tokens/{token_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /**
         * Revoke Token
         * @description Stops working at once. A revoked token stays listed, so you can see what it was.
         */
        delete: operations["revoke_token_api_v1_tokens__token_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tokens/current": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Current Token
         * @description Who this is: the extension checks its token here, and speaks the owner's language.
         */
        get: operations["current_token_api_v1_tokens_current_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/applications/{application_id}/fill": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Fill Sheet
         * @description What goes into the application's form: profile values, saved answers, documents (with their PDFs).
         */
        get: operations["fill_sheet_api_v1_applications__application_id__fill_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/copy-sheet": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Copy Sheet
         * @description A profile's values for the extension's copy panel (the pack's default profile unless one is chosen), each
         *     ready to paste, and the saved answers. Needs a token with profiles:read, or a session.
         */
        get: operations["copy_sheet_api_v1_copy_sheet_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auto/settings": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Auto Settings */
        get: operations["auto_settings_api_v1_auto_settings_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Update Auto Settings
         * @description Pause Auto (no new runs, and none prepared further), and its limits.
         */
        patch: operations["update_auto_settings_api_v1_auto_settings_patch"];
        trace?: never;
    };
    "/api/v1/auto/counts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Auto Counts */
        get: operations["auto_counts_api_v1_auto_counts_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auto/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Runs */
        get: operations["list_runs_api_v1_auto_runs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auto/runs/{run_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Run */
        get: operations["get_run_api_v1_auto_runs__run_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auto/runs/{run_id}/stop": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Stop Run
         * @description Stop preparing it, or take it off Ready for you. Its application and documents stay.
         */
        post: operations["stop_run_api_v1_auto_runs__run_id__stop_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auto/runs/{run_id}/retry": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Retry Run
         * @description Start again from the gate, once what it needed is fixed. Not after a send (from before) that may have gone.
         */
        post: operations["retry_run_api_v1_auto_runs__run_id__retry_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auto/runs/{run_id}/dismiss": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Dismiss Run */
        post: operations["dismiss_run_api_v1_auto_runs__run_id__dismiss_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auto/runs/{run_id}/screenshots/{screenshot_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Run Screenshot */
        get: operations["run_screenshot_api_v1_auto_runs__run_id__screenshots__screenshot_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AddedDefaults */
        AddedDefaults: {
            /** Added */
            added: number;
        };
        /** AnswerChanges */
        AnswerChanges: {
            /** Answer */
            answer?: string | null;
            /** Question */
            question?: {
                [key: string]: string;
            } | null;
            /** Is Sensitive */
            is_sensitive?: boolean | null;
        };
        /** AnswerOut */
        AnswerOut: {
            /** Id */
            id: string;
            /** Pack */
            pack: string;
            /** Key */
            key: string;
            question: components["schemas"]["Label"];
            /** Answer */
            answer: string;
            /**
             * Answer Type
             * @enum {string}
             */
            answer_type: "text" | "yes_no" | "choice" | "number" | "url";
            /** Choices */
            choices: components["schemas"]["Choice"][];
            /** Is Sensitive */
            is_sensitive: boolean;
            /**
             * Source
             * @enum {string}
             */
            source: "user" | "learned" | "pack";
        };
        /** Answers */
        Answers: {
            /** Items */
            items: components["schemas"]["AnswerOut"][];
        };
        /** ApplicationChanges */
        ApplicationChanges: {
            /** Profile Id */
            profile_id?: string | null;
            /** Notes */
            notes?: string | null;
        };
        /** ApplicationOut */
        ApplicationOut: {
            /** Id */
            id: string;
            opportunity: components["schemas"]["OpportunitySummary"];
            /** Profile Id */
            profile_id: string | null;
            /** Pipeline Id */
            pipeline_id: string;
            stage: components["schemas"]["StageRef"];
            /** Current Documents */
            current_documents: components["schemas"]["DocumentState"][];
            /** Submitted At */
            submitted_at: string | null;
            /** Notes */
            notes: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** Applications */
        Applications: {
            /** Items */
            items: components["schemas"]["ApplicationOut"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** AutoCounts */
        AutoCounts: {
            /**
             * Waiting
             * @description Being prepared
             */
            waiting: number;
            /**
             * Ready
             * @description Prepared: the person's to send
             */
            ready: number;
            /** Needs You */
            needs_you: number;
            /** Sent */
            sent: number;
        };
        /** AutoRunOut */
        AutoRunOut: {
            /** Id */
            id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "starting" | "writing" | "ready" | "sent" | "needs_you" | "stopped" | "dismissed";
            reason: components["schemas"]["ErrorCode"] | null;
            /** Reason Detail */
            reason_detail: {
                [key: string]: unknown;
            };
            /** Match Id */
            match_id: string;
            /** Application Id */
            application_id: string | null;
            /** Search Id */
            search_id: string | null;
            opportunity: components["schemas"]["OpportunitySummary"];
            /** Score */
            score: number | null;
            /**
             * Ready At
             * @description When it was prepared: the person's to send from then
             */
            ready_at: string | null;
            /**
             * Drafts
             * @description Answers a runner drafted, on runs from before (history)
             */
            drafts: {
                [key: string]: unknown;
            }[];
            /**
             * Screenshots
             * @description A runner's screenshots, on runs from before
             */
            screenshots: components["schemas"]["AutoScreenshotRef"][];
            /** Submission Id */
            submission_id: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /** Finished At */
            finished_at: string | null;
        };
        /** AutoRuns */
        AutoRuns: {
            /** Items */
            items: components["schemas"]["AutoRunOut"][];
        };
        /** AutoScreenshotRef */
        AutoScreenshotRef: {
            /** Id */
            id: string;
            /** Step */
            step: string;
            /** Size */
            size: number;
        };
        /** AutoSettings */
        AutoSettings: {
            /** Auto Paused */
            auto_paused: boolean;
            /** Auto Min Score */
            auto_min_score: number;
            /** Auto Daily Cap */
            auto_daily_cap: number;
        };
        /** AutoSettingsChanges */
        AutoSettingsChanges: {
            /** Auto Paused */
            auto_paused?: boolean | null;
            /** Auto Min Score */
            auto_min_score?: number | null;
            /** Auto Daily Cap */
            auto_daily_cap?: number | null;
        };
        /** Body_import_profile_api_v1_profiles_import_post */
        Body_import_profile_api_v1_profiles_import_post: {
            /**
             * File
             * @description A resume (or the pack's document): PDF, .docx or text
             */
            file: string;
            /**
             * Pack
             * @default job
             */
            pack?: string;
            /** Name */
            name?: string | null;
            /** Is Default */
            is_default?: boolean | null;
        };
        /** BriefingContent */
        BriefingContent: {
            new_matches: components["schemas"]["BriefingNewMatches"];
            /** Follow Ups */
            follow_ups: components["schemas"]["BriefingFollowUp"][];
            /** Deadlines */
            deadlines: components["schemas"]["BriefingDeadline"][];
        };
        /** BriefingDeadline */
        BriefingDeadline: {
            /**
             * Pack
             * @default job
             */
            pack?: string;
            /** Application Id */
            application_id: string;
            /** Title */
            title: string;
            /** Issuer Name */
            issuer_name: string;
            /**
             * Deadline
             * Format: date-time
             */
            deadline: string;
        };
        /** BriefingFollowUp */
        BriefingFollowUp: {
            /**
             * Pack
             * @default job
             */
            pack?: string;
            /** Application Id */
            application_id: string;
            /** Title */
            title: string;
            /** Issuer Name */
            issuer_name: string;
            /** Stage Code */
            stage_code: string;
            /** Days */
            days: number;
        };
        /** BriefingMatch */
        BriefingMatch: {
            /**
             * Pack
             * @default job
             */
            pack?: string;
            /** Match Id */
            match_id: string;
            /** Opportunity Id */
            opportunity_id: string;
            /** Title */
            title: string;
            /** Issuer Name */
            issuer_name: string;
            /** Score */
            score: number | null;
        };
        /** BriefingNewMatches */
        BriefingNewMatches: {
            /** Count */
            count: number;
            /** Top */
            top: components["schemas"]["BriefingMatch"][];
        };
        /** BriefingOut */
        BriefingOut: {
            /** Date */
            date: string;
            content: components["schemas"]["BriefingContent"];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /**
         * Caller
         * @description Who a request is: the owner, and the token it came with (None for a session).
         */
        Caller: {
            /** Email */
            email: string;
            /**
             * Locale
             * @enum {string}
             */
            locale: "en" | "ne" | "es";
            token: components["schemas"]["TokenOut"] | null;
            /**
             * Web Url
             * @description The web app, for links back to it
             */
            web_url?: string | null;
        };
        /** Choice */
        Choice: {
            /** Value */
            value: string;
            label: components["schemas"]["Label"];
        };
        /** ChooseModel */
        ChooseModel: {
            /** Base Url */
            base_url: string;
            /** Model */
            model: string;
            /**
             * Writing Model
             * @default
             */
            writing_model?: string;
            /** Num Ctx */
            num_ctx?: number | null;
        };
        /** ClaimWarning */
        ClaimWarning: {
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "confirm" | "number" | "unsupported";
            /** Quote */
            quote: string;
            /** Reason */
            reason: string;
            /** Resolved */
            resolved?: "kept" | null;
        };
        /** CopyGroupOut */
        CopyGroupOut: {
            /**
             * Title
             * @description The person's own words for the entry (a job, a qualification), or empty
             */
            title: string;
            /** Items */
            items: components["schemas"]["CopyItemOut"][];
        };
        /** CopyItemOut */
        CopyItemOut: {
            /** Label */
            label: {
                [key: string]: string;
            };
            /** Value */
            value: string;
            /**
             * Sensitive
             * @description An equal-opportunity answer: shown only after the person asks
             */
            sensitive: boolean;
        };
        /** CopyProfile */
        CopyProfile: {
            /** Id */
            id: string;
            /** Pack */
            pack: string;
            /** Name */
            name: string;
            /** Is Default */
            is_default: boolean;
        };
        /**
         * CopySheetOut
         * @description A profile's values, each ready to copy and paste into any form; no profile yet: profile null.
         */
        CopySheetOut: {
            profile: components["schemas"]["CopyProfile"] | null;
            /** Profiles */
            profiles: components["schemas"]["CopyProfile"][];
            /** Tabs */
            tabs: components["schemas"]["CopyTabOut"][];
        };
        /** CopyTabOut */
        CopyTabOut: {
            /** Key */
            key: string;
            /** Label */
            label: {
                [key: string]: string;
            };
            /** Groups */
            groups: components["schemas"]["CopyGroupOut"][];
        };
        /** CreatedToken */
        CreatedToken: {
            token: components["schemas"]["TokenOut"];
            /**
             * Secret
             * @description Shown this once; only its hash is kept
             */
            secret: string;
        };
        /** Criteria */
        Criteria: {
            /** Keywords */
            keywords?: string[];
            /**
             * Match All
             * @default false
             */
            match_all?: boolean;
            /** Exclude */
            exclude?: string[];
            /** Locations */
            locations?: string[];
            /**
             * Remote Only
             * @default false
             */
            remote_only?: boolean;
            /**
             * Needs Sponsorship
             * @default false
             */
            needs_sponsorship?: boolean;
            /** Source Ids */
            source_ids?: string[];
        };
        /** Dealbreaker */
        Dealbreaker: {
            /** Text */
            text: string;
            /** Code */
            code?: string | null;
        };
        /** DocumentContent */
        DocumentContent: {
            /** Content Markdown */
            content_markdown: string;
        };
        /** DocumentOut */
        DocumentOut: {
            /** Id */
            id: string;
            /** Application Id */
            application_id: string;
            /** Document Type */
            document_type: string;
            /**
             * Status
             * @enum {string}
             */
            status: "pending" | "ready" | "failed";
            error_code: components["schemas"]["ErrorCode"] | null;
            /** Version */
            version: number;
            /** Is Active */
            is_active: boolean;
            /** Content Markdown */
            content_markdown: string;
            /** Claim Warnings */
            claim_warnings: components["schemas"]["ClaimWarning"][];
            /**
             * Claims Status
             * @enum {string}
             */
            claims_status: "pending" | "checked" | "failed" | "skipped";
            /** Claims Checked At */
            claims_checked_at: string | null;
            /** Reviewed At */
            reviewed_at: string | null;
            /**
             * Source
             * @enum {string}
             */
            source: "generated" | "uploaded" | "imported" | "edited";
            /** Model */
            model: string | null;
            /** Generation Ms */
            generation_ms: number | null;
            /** Profile Id */
            profile_id: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Finished At */
            finished_at: string | null;
        };
        /** DocumentRequest */
        DocumentRequest: {
            /** Document Type */
            document_type: string;
            /** Profile Id */
            profile_id?: string | null;
        };
        /**
         * DocumentState
         * @description A document in use, or one being written or failed since: enough for a card.
         */
        DocumentState: {
            /** Id */
            id: string;
            /** Document Type */
            document_type: string;
            /**
             * Status
             * @enum {string}
             */
            status: "pending" | "ready" | "failed";
            /** Version */
            version: number;
        };
        /** DocumentTypeOut */
        DocumentTypeOut: {
            /** Key */
            key: string;
            label: components["schemas"]["Label"];
            description: components["schemas"]["Label"];
            /** Generatable */
            generatable: boolean;
            /** Accepts Upload */
            accepts_upload: boolean;
            /**
             * Layout
             * @enum {string}
             */
            layout: "sections" | "letter";
        };
        /** Documents */
        Documents: {
            /** Items */
            items: components["schemas"]["DocumentOut"][];
        };
        /** DuplicateProfile */
        DuplicateProfile: {
            /** Name */
            name?: string | null;
        };
        /** EndpointOut */
        EndpointOut: {
            /**
             * Api
             * @description native: /api/chat and /api/tags; v1: /v1/chat/completions
             * @enum {string}
             */
            api: "native" | "v1";
            /** Base Url */
            base_url: string;
            /** Version */
            version: string | null;
            /** Models */
            models: components["schemas"]["FoundModelOut"][];
        };
        /**
         * ErrorCode
         * @enum {string}
         */
        ErrorCode: "INTERNAL" | "VALIDATION_FAILED" | "NOT_FOUND" | "METHOD_NOT_ALLOWED" | "TOO_MANY_REQUESTS" | "DATABASE_NOT_READY" | "UNAUTHENTICATED" | "SIGN_IN_FAILED" | "SIGN_IN_LOCKED" | "ORIGIN_NOT_ALLOWED" | "OWNER_EXISTS" | "REGISTRATION_CLOSED" | "EMAIL_TAKEN" | "ACCOUNT_DISABLED" | "OWNER_ONLY" | "ACCOUNT_IS_OWNER" | "PASSWORD_TOO_SHORT" | "RESET_LINK_INVALID" | "MAIL_NOT_SET_UP" | "TOKEN_INVALID" | "TOKEN_NOT_ALLOWED" | "TOKEN_SCOPE_MISSING" | "TOKEN_NOT_FOUND" | "PACK_NOT_FOUND" | "DOCUMENT_TYPE_NOT_FOUND" | "DOCUMENT_TYPE_NOT_GENERATABLE" | "INVALID_ATTRIBUTES" | "PROFILE_NOT_FOUND" | "PROFILE_REQUIRED" | "PROFILE_PACK_MISMATCH" | "PROFILE_NOT_READ" | "UPLOAD_TOO_LARGE" | "UPLOAD_UNSUPPORTED" | "UPLOAD_NO_TEXT" | "TEMPLATE_PROBLEMS" | "STORAGE_UNAVAILABLE" | "OPPORTUNITY_NOT_FOUND" | "URL_OR_TEXT_REQUIRED" | "URL_NOT_ALLOWED" | "ADDRESS_NOT_ALLOWED" | "FETCH_FAILED" | "FETCH_BLOCKED" | "FETCH_NOT_HTML" | "FETCH_TOO_LARGE" | "FETCH_TOO_LITTLE_TEXT" | "FETCH_TOO_MANY_REDIRECTS" | "EXTRACT_FAILED" | "APPLICATION_NOT_FOUND" | "APPLICATION_EXISTS" | "STAGE_NOT_FOUND" | "DOCUMENT_NOT_FOUND" | "SOURCE_NOT_FOUND" | "SOURCE_KIND_NOT_FOUND" | "SOURCE_TOO_SOON" | "SOURCE_NOT_RECOGNISED" | "SOURCE_FAILED" | "SEARCH_NOT_FOUND" | "MATCH_NOT_FOUND" | "SCORE_CAP_REACHED" | "DOCUMENT_NOT_READY" | "WARNING_NOT_FOUND" | "RENDER_PENDING" | "ANSWER_NOT_FOUND" | "ANSWER_EXISTS" | "SUBMISSION_NOT_FOUND" | "UNDO_TOO_LATE" | "AUTO_RUN_NOT_FOUND" | "AUTO_ACTION_NOT_ALLOWED" | "RUNNER_TASK_NOT_FOUND" | "AUTO_PAUSED" | "AUTO_CAP_REACHED" | "AUTO_SAME_ISSUER" | "AUTO_CLOSED" | "AUTO_UNSUPPORTED_BOARD" | "AUTO_PROFILE_REQUIRED" | "AUTO_DOCUMENT_FAILED" | "AUTO_CLAIMS_UNCHECKED" | "AUTO_CLAIM_WARNINGS" | "AUTO_TIMED_OUT" | "AUTO_CAPTCHA" | "AUTO_SIGN_IN" | "AUTO_FORM_MISSING" | "AUTO_CONSENT_REQUIRED" | "AUTO_REQUIRED_UNANSWERED" | "AUTO_DRAFT_UNSUPPORTED" | "AUTO_DOCUMENTS_CHANGED" | "AUTO_FORM_CHANGED" | "AUTO_VALIDATION_ERROR" | "AUTO_NO_CONFIRMATION" | "AUTO_SEND_UNKNOWN" | "AUTO_RUNNER_FAILED" | "LLM_UNREACHABLE" | "LLM_TIMEOUT" | "LLM_BAD_REPLY" | "LLM_EMPTY_REPLY" | "LLM_MODEL_MISSING" | "MODEL_NOT_FOUND" | "MODEL_TEST_FAILED";
        /** Extraction */
        Extraction: {
            /**
             * Status
             * @enum {string}
             */
            status: "pending" | "ready" | "manual";
            /**
             * Method
             * @enum {string}
             */
            method: "json_ld" | "model" | "manual" | "import" | "source";
            error_code?: components["schemas"]["ErrorCode"] | null;
            /**
             * Edited
             * @default false
             */
            edited?: boolean;
        };
        /** FieldError */
        FieldError: {
            /** Loc */
            loc: (string | number)[];
            /** Msg */
            msg: string;
            /** Type */
            type: string;
        };
        /** FillDocument */
        FillDocument: {
            /** Document Id */
            document_id: string;
            /** Document Type */
            document_type: string;
            label: components["schemas"]["Label"];
            /** Version */
            version: number;
            /** Filename */
            filename: string;
            /** Pdf Path */
            pdf_path: string;
            /** Reviewed */
            reviewed: boolean;
            /** Open Warnings */
            open_warnings: number;
        };
        /**
         * FillSheet
         * @description Everything the extension puts into a form. Sensitive answers go only to the form, never to a model.
         */
        FillSheet: {
            application: components["schemas"]["ApplicationOut"];
            opportunity: components["schemas"]["OpportunityOut"];
            /** Values */
            values: {
                [key: string]: string;
            };
            /** Answers */
            answers: components["schemas"]["AnswerOut"][];
            /** Documents */
            documents: components["schemas"]["FillDocument"][];
        };
        /**
         * Filled
         * @description What the extension did to the form: counts and labels only, never the values.
         */
        Filled: {
            /**
             * Fields
             * @default 0
             */
            fields?: number;
            /** Files */
            files?: string[];
            /** Left Blank */
            left_blank?: string[];
        };
        /** ForgotPassword */
        ForgotPassword: {
            /** Email */
            email: string;
        };
        /** FoundModelOut */
        FoundModelOut: {
            /** Name */
            name: string;
            /** Size Bytes */
            size_bytes: number | null;
            /**
             * Parameters
             * @description As the server says it: "8.2B"
             */
            parameters: string | null;
            /** Family */
            family: string | null;
            /** Quantization */
            quantization: string | null;
            /** Context Length */
            context_length: number | null;
            /**
             * Loaded
             * @description In memory now: answers without loading first
             */
            loaded: boolean;
            /**
             * Usable
             * @description Writes text; an embedding model can't be chosen
             */
            usable: boolean;
            /** Note */
            note: "embedding" | null;
        };
        /** Health */
        Health: {
            /**
             * Status
             * @enum {string}
             */
            status: "ok" | "degraded";
            /** Database */
            database: boolean;
            /** Storage */
            storage: boolean;
            /** Version */
            version: string;
        };
        /** History */
        History: {
            /** Items */
            items: components["schemas"]["HistoryEntry"][];
        };
        /** HistoryEntry */
        HistoryEntry: {
            /** Id */
            id: string;
            stage: components["schemas"]["StageRef"];
            /**
             * Entered At
             * Format: date-time
             */
            entered_at: string;
            /** Exited At */
            exited_at: string | null;
            /** Outcome */
            outcome: string;
            /** Note */
            note: string;
        };
        /** Kit */
        Kit: {
            application: components["schemas"]["ApplicationOut"];
            /** Apply Url */
            apply_url: string | null;
            /** Documents */
            documents: components["schemas"]["KitDocument"][];
            /** Answers */
            answers: components["schemas"]["AnswerOut"][];
            /** Submissions */
            submissions: components["schemas"]["SubmissionOut"][];
        };
        /** KitDocument */
        KitDocument: {
            document: components["schemas"]["DocumentOut"];
            label: components["schemas"]["Label"];
            /** Open Warnings */
            open_warnings: number;
        };
        /**
         * Label
         * @description One string in each of apply's languages. A label stored before Spanish was added (a saved answer's question,
         *     say) has only English and Nepali, and a Spanish reader sees the English.
         */
        Label: {
            /** En */
            en: string;
            /** Ne */
            ne: string;
            /** Es */
            es?: string | null;
        };
        /** Lookup */
        Lookup: {
            opportunity: components["schemas"]["OpportunityOut"];
            application: components["schemas"]["ApplicationOut"] | null;
        };
        /** MatchChanges */
        MatchChanges: {
            /**
             * Status
             * @enum {string}
             */
            status: "new" | "saved" | "dismissed";
        };
        /** MatchCounts */
        MatchCounts: {
            /** New */
            new: number;
            /** Saved */
            saved: number;
            /** Dismissed */
            dismissed: number;
            /** Tracked */
            tracked: number;
        };
        /** MatchOpportunity */
        MatchOpportunity: {
            /** Id */
            id: string;
            /** Pack */
            pack: string;
            /** Title */
            title: string;
            /** Issuer Name */
            issuer_name: string;
            /**
             * Status
             * @enum {string}
             */
            status: "open" | "closed" | "rolling" | "draft";
            /** Source Id */
            source_id: string | null;
            /** Source Url */
            source_url: string | null;
            /** Apply Url */
            apply_url: string | null;
            /** Posted At */
            posted_at: string | null;
            /** Deadline */
            deadline: string | null;
            /** Attributes */
            attributes: {
                [key: string]: unknown;
            };
        };
        /** MatchOut */
        MatchOut: {
            /** Id */
            id: string;
            opportunity: components["schemas"]["MatchOpportunity"];
            /** Search Ids */
            search_ids: string[];
            /**
             * Status
             * @enum {string}
             */
            status: "new" | "saved" | "dismissed" | "tracked";
            /** Prefilter */
            prefilter: {
                [key: string]: unknown;
            };
            /** Score */
            score: number | null;
            /** Score Reasons */
            score_reasons: string[];
            /** Dealbreakers */
            dealbreakers: components["schemas"]["Dealbreaker"][];
            /**
             * Score Status
             * @enum {string}
             */
            score_status: "pending" | "scored" | "failed" | "capped";
            score_error_code: components["schemas"]["ErrorCode"] | null;
            /** Scored At */
            scored_at: string | null;
            /** Model */
            model: string | null;
            /** Application Id */
            application_id: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** Matches */
        Matches: {
            /** Items */
            items: components["schemas"]["MatchOut"][];
            /** Next Cursor */
            next_cursor: string | null;
            counts: components["schemas"]["MatchCounts"];
        };
        /** Me */
        Me: {
            /** Id */
            id: string;
            /** Email */
            email: string;
            /**
             * Locale
             * @enum {string}
             */
            locale: "en" | "ne" | "es";
            /** Is Owner */
            is_owner: boolean;
            /** Time Zone */
            time_zone: string;
            /** Briefing Hour */
            briefing_hour: number;
        };
        /** MeChanges */
        MeChanges: {
            /** Locale */
            locale?: ("en" | "ne" | "es") | null;
            /** Time Zone */
            time_zone?: string | null;
            /** Briefing Hour */
            briefing_hour?: number | null;
        };
        /** ModelChosen */
        ModelChosen: {
            current: components["schemas"]["ModelInUse"];
            /**
             * Milliseconds
             * @description How long the test took (the first use loads the model)
             */
            milliseconds: number;
        };
        /** ModelInUse */
        ModelInUse: {
            /**
             * Api
             * @enum {string}
             */
            api: "native" | "v1";
            /** Base Url */
            base_url: string;
            /** Model */
            model: string;
            /** Writing Model */
            writing_model: string;
            /**
             * Num Ctx
             * @description The context size sent (native API); None where the server sets its own
             */
            num_ctx: number | null;
            /**
             * Source
             * @description Chosen in Settings → Model, or the settings (.env)
             * @enum {string}
             */
            source: "chosen" | "settings";
        };
        /** ModelStatus */
        ModelStatus: {
            /** Reachable */
            reachable: boolean;
            /** Ready */
            ready: boolean;
            /** Base Url */
            base_url: string;
            /** Version */
            version: string | null;
            /** Wanted */
            wanted: string[];
            /** Installed */
            installed: string[];
            /** Missing */
            missing: string[];
            /** Num Ctx */
            num_ctx: number | null;
        };
        /** Models */
        Models: {
            current: components["schemas"]["ModelInUse"];
            /** Endpoints */
            endpoints: components["schemas"]["EndpointOut"][];
        };
        /** Move */
        Move: {
            /** Stage Code */
            stage_code: string;
            /**
             * Note
             * @default
             */
            note?: string;
        };
        /** NewAnswer */
        NewAnswer: {
            /**
             * Pack
             * @default job
             */
            pack?: string;
            /** Key */
            key: string;
            /** Question */
            question: {
                [key: string]: string;
            };
            /**
             * Answer
             * @default
             */
            answer?: string;
            /**
             * Answer Type
             * @default text
             * @enum {string}
             */
            answer_type?: "text" | "yes_no" | "number" | "url";
            /**
             * Is Sensitive
             * @default false
             */
            is_sensitive?: boolean;
        };
        /** NewApplication */
        NewApplication: {
            /** Opportunity Id */
            opportunity_id: string;
            /** Profile Id */
            profile_id?: string | null;
            /**
             * Notes
             * @default
             */
            notes?: string;
        };
        /** NewProfile */
        NewProfile: {
            /**
             * Pack
             * @default job
             */
            pack?: string;
            /**
             * Kind
             * @default individual
             * @enum {string}
             */
            kind?: "individual" | "organisation";
            /** Name */
            name: string;
            /**
             * Summary
             * @default
             */
            summary?: string;
            /** Attributes */
            attributes?: {
                [key: string]: unknown;
            };
            /**
             * Tone Instructions
             * @default
             */
            tone_instructions?: string;
            /** Is Default */
            is_default?: boolean | null;
        };
        /** NewSearch */
        NewSearch: {
            /**
             * Pack
             * @default job
             */
            pack?: string;
            /** Name */
            name: string;
            criteria?: components["schemas"]["Criteria"];
            /** Profile Id */
            profile_id?: string | null;
            /**
             * Min Score
             * @default 0
             */
            min_score?: number;
            /**
             * Enabled
             * @default true
             */
            enabled?: boolean;
            /**
             * Auto Enabled
             * @default false
             */
            auto_enabled?: boolean;
        };
        /** NewSource */
        NewSource: {
            /**
             * Pack
             * @default job
             */
            pack?: string;
            /** Kind */
            kind: string;
            /** Config */
            config: {
                [key: string]: string;
            };
            /** Name */
            name?: string | null;
            /**
             * Interval Hours
             * @default 6
             */
            interval_hours?: number;
            /**
             * Enabled
             * @default true
             */
            enabled?: boolean;
        };
        /** NewSubmission */
        NewSubmission: {
            /**
             * Note
             * @default
             */
            note?: string;
            /** Confirmation Url */
            confirmation_url?: string | null;
            filled?: components["schemas"]["Filled"] | null;
        };
        /** NewToken */
        NewToken: {
            /** Name */
            name: string;
            /**
             * Kind
             * @default extension
             * @constant
             */
            kind?: "extension";
            /** Scopes */
            scopes: ("applications:read" | "applications:write" | "submissions:write" | "profiles:read")[];
            /**
             * Expires In Days
             * @default 90
             */
            expires_in_days?: (30 | 90 | 365) | null;
        };
        /** Opportunities */
        Opportunities: {
            /** Items */
            items: components["schemas"]["OpportunityOut"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** OpportunityChanges */
        OpportunityChanges: {
            /** Title */
            title?: string | null;
            /** Issuer Name */
            issuer_name?: string | null;
            /** Apply Url */
            apply_url?: string | null;
            /** Deadline */
            deadline?: string | null;
            /** Status */
            status?: ("open" | "closed" | "rolling" | "draft") | null;
            /** Attributes */
            attributes?: {
                [key: string]: unknown;
            } | null;
        };
        /** OpportunityOut */
        OpportunityOut: {
            /** Id */
            id: string;
            /** Pack */
            pack: string;
            /** Title */
            title: string;
            /** Issuer Name */
            issuer_name: string;
            /** Source Url */
            source_url: string | null;
            /** Apply Url */
            apply_url: string | null;
            /** Deadline */
            deadline: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "open" | "closed" | "rolling" | "draft";
            /** Attributes */
            attributes: {
                [key: string]: unknown;
            };
            extraction: components["schemas"]["Extraction"];
            /**
             * First Seen At
             * Format: date-time
             */
            first_seen_at: string;
            /**
             * Last Seen At
             * Format: date-time
             */
            last_seen_at: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** OpportunitySummary */
        OpportunitySummary: {
            /** Id */
            id: string;
            /** Pack */
            pack: string;
            /** Title */
            title: string;
            /** Issuer Name */
            issuer_name: string;
            /** Deadline */
            deadline: string | null;
            /** Apply Url */
            apply_url: string | null;
            /** Source Url */
            source_url: string | null;
            extraction: components["schemas"]["Extraction"];
        };
        /** PackOut */
        PackOut: {
            /** Key */
            key: string;
            /** Version */
            version: string;
            label: components["schemas"]["Label"];
            description: components["schemas"]["Label"];
            /** Profile Kinds */
            profile_kinds: ("individual" | "organisation")[];
            /** Search Options */
            search_options: ("locations" | "remote_only" | "needs_sponsorship")[];
            /** Auto */
            auto: boolean;
            /** Profile Schema */
            profile_schema: {
                [key: string]: unknown;
            };
            /** Opportunity Schema */
            opportunity_schema: {
                [key: string]: unknown;
            };
            /** Document Types */
            document_types: components["schemas"]["DocumentTypeOut"][];
            pipeline: components["schemas"]["PipelineOut"];
            /** Category Labels */
            category_labels: {
                [key: string]: components["schemas"]["Label"];
            };
            /** Action Labels */
            action_labels: {
                [key: string]: components["schemas"]["Label"];
            };
            /** Profile Kind Labels */
            profile_kind_labels: {
                [key: string]: components["schemas"]["Label"];
            };
        };
        /** Packs */
        Packs: {
            /** Items */
            items: components["schemas"]["PackOut"][];
        };
        /**
         * Paste
         * @description A link to a posting, or its text: one of the two.
         */
        Paste: {
            /**
             * Pack
             * @default job
             */
            pack?: string;
            /** Url */
            url?: string | null;
            /** Text */
            text?: string | null;
            /** Html */
            html?: string | null;
        };
        /** People */
        People: {
            /** Items */
            items: components["schemas"]["PersonOut"][];
        };
        /**
         * PersonOut
         * @description An account, as the owner sees it: never anything in it.
         */
        PersonOut: {
            /** Id */
            id: string;
            /** Email */
            email: string;
            /** Is Owner */
            is_owner: boolean;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Last Sign In At */
            last_sign_in_at: string | null;
            /** Disabled At */
            disabled_at: string | null;
        };
        /** PipelineOut */
        PipelineOut: {
            /** Id */
            id: string;
            /** Key */
            key: string;
            label: components["schemas"]["Label"];
            /** Stages */
            stages: components["schemas"]["StageOut"][];
        };
        /**
         * Problem
         * @description RFC 9457 Problem Details, with a stable ``code`` the web app translates. ``detail`` is for logs.
         */
        Problem: {
            /** Type */
            type: string;
            /** Status */
            status: number;
            /** Title */
            title: string;
            /** Detail */
            detail: string;
            code: components["schemas"]["ErrorCode"];
            /** Errors */
            errors?: components["schemas"]["FieldError"][] | null;
            /** Application Id */
            application_id?: string | null;
            /** Retry After */
            retry_after?: number | null;
        };
        /** ProfileChanges */
        ProfileChanges: {
            /** Name */
            name?: string | null;
            /** Summary */
            summary?: string | null;
            /** Attributes */
            attributes?: {
                [key: string]: unknown;
            } | null;
            /** Tone Instructions */
            tone_instructions?: string | null;
            /** Is Default */
            is_default?: boolean | null;
        };
        /** ProfileOut */
        ProfileOut: {
            /** Id */
            id: string;
            /** Pack */
            pack: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "individual" | "organisation";
            /** Name */
            name: string;
            /** Summary */
            summary: string;
            /** Attributes */
            attributes: {
                [key: string]: unknown;
            };
            /** Tone Instructions */
            tone_instructions: string;
            /** Is Default */
            is_default: boolean;
            source?: components["schemas"]["ProfileSource"] | null;
            reading?: components["schemas"]["ProfileReading"] | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * ProfileReading
         * @description The model reading the document into the fields: pending, ready, failed (error_code says why), or stopped
         *     (the person edited the profile first, and their edits win).
         */
        ProfileReading: {
            /**
             * Status
             * @enum {string}
             */
            status: "pending" | "ready" | "failed" | "stopped";
            error_code?: components["schemas"]["ErrorCode"] | null;
            /**
             * Edited
             * @default false
             */
            edited?: boolean;
        };
        /**
         * ProfileSource
         * @description The document a profile was made from (download it at /profiles/{id}/source).
         */
        ProfileSource: {
            /** Name */
            name: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "pdf" | "docx" | "text";
            /** Size */
            size: number;
        };
        /** Profiles */
        Profiles: {
            /** Items */
            items: components["schemas"]["ProfileOut"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** RecognisedSource */
        RecognisedSource: {
            /** Kind */
            kind: string;
            /** Config */
            config: {
                [key: string]: string;
            };
        };
        /** Register */
        Register: {
            /** Email */
            email: string;
            /** Password */
            password: string;
            /**
             * Locale
             * @default en
             * @enum {string}
             */
            locale?: "en" | "ne" | "es";
            /**
             * Demo
             * @description Add the demo (John Doe, a fictional profile) to look around
             * @default false
             */
            demo?: boolean;
        };
        /**
         * Registration
         * @description Whether anyone may create an account on this apply (the owner's switch).
         */
        Registration: {
            /** Open */
            open: boolean;
        };
        /**
         * ResetFor
         * @description The account a reset link is for (shown, and given to a password manager).
         */
        ResetFor: {
            /** Email */
            email: string;
        };
        /** ResetPassword */
        ResetPassword: {
            /** Token */
            token: string;
            /** Password */
            password: string;
        };
        /** ResetToken */
        ResetToken: {
            /** Token */
            token: string;
        };
        /** Reviewed */
        Reviewed: {
            /**
             * Reviewed
             * @default true
             */
            reviewed?: boolean;
        };
        /** SearchChanges */
        SearchChanges: {
            /** Name */
            name?: string | null;
            criteria?: components["schemas"]["Criteria"] | null;
            /** Profile Id */
            profile_id?: string | null;
            /** Min Score */
            min_score?: number | null;
            /** Enabled */
            enabled?: boolean | null;
            /** Auto Enabled */
            auto_enabled?: boolean | null;
        };
        /** SearchOut */
        SearchOut: {
            /** Id */
            id: string;
            /** Pack */
            pack: string;
            /** Name */
            name: string;
            criteria: components["schemas"]["Criteria"];
            /** Profile Id */
            profile_id: string | null;
            /** Min Score */
            min_score: number;
            /** Enabled */
            enabled: boolean;
            /** Auto Enabled */
            auto_enabled: boolean;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** Searches */
        Searches: {
            /** Items */
            items: components["schemas"]["SearchOut"][];
        };
        /**
         * Setup
         * @description Whether "Create an account" is offered, and whether it's the first run (the owner's account).
         */
        Setup: {
            /** Open */
            open: boolean;
            /** First Run */
            first_run: boolean;
            /**
             * Mail
             * @default false
             */
            mail?: boolean;
        };
        /** SignIn */
        SignIn: {
            /** Email */
            email: string;
            /** Password */
            password: string;
        };
        /** SourceAddress */
        SourceAddress: {
            /**
             * Pack
             * @default job
             */
            pack?: string;
            /** Url */
            url: string;
        };
        /** SourceChanges */
        SourceChanges: {
            /** Config */
            config?: {
                [key: string]: string;
            } | null;
            /** Name */
            name?: string | null;
            /** Interval Hours */
            interval_hours?: number | null;
            /** Enabled */
            enabled?: boolean | null;
        };
        /** SourceField */
        SourceField: {
            /** Key */
            key: string;
            label: components["schemas"]["Label"];
            hint: components["schemas"]["Label"];
            /** Required */
            required: boolean;
        };
        /** SourceKind */
        SourceKind: {
            /** Kind */
            kind: string;
            /** From Address */
            from_address: boolean;
            label: components["schemas"]["Label"];
            description: components["schemas"]["Label"];
            terms: components["schemas"]["Label"];
            /** Attribution */
            attribution: string | null;
            /** Min Interval Hours */
            min_interval_hours: number;
            /** Fields */
            fields: components["schemas"]["SourceField"][];
        };
        /** SourceKinds */
        SourceKinds: {
            /** Items */
            items: components["schemas"]["SourceKind"][];
        };
        /** SourceOut */
        SourceOut: {
            /** Id */
            id: string;
            /** Pack */
            pack: string;
            /** Kind */
            kind: string;
            /** Name */
            name: string;
            /** Config */
            config: {
                [key: string]: string;
            };
            /** Enabled */
            enabled: boolean;
            /** Interval Hours */
            interval_hours: number;
            /** Last Fetched At */
            last_fetched_at: string | null;
            /**
             * Last Status
             * @enum {string}
             */
            last_status: "never" | "ok" | "failed";
            last_error_code: components["schemas"]["ErrorCode"] | null;
            /** Last Count */
            last_count: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** Sources */
        Sources: {
            /** Items */
            items: components["schemas"]["SourceOut"][];
        };
        /** StageOut */
        StageOut: {
            /** Id */
            id: string;
            /** Code */
            code: string;
            label: components["schemas"]["Label"];
            /** Position */
            position: number;
            /**
             * Category
             * @enum {string}
             */
            category: "pre_pipeline" | "active" | "success" | "failure" | "paused";
            /** Action Type */
            action_type: string;
            /** Is Terminal */
            is_terminal: boolean;
            /** Follow Up After Days */
            follow_up_after_days: number | null;
            /** Expected Duration Days */
            expected_duration_days: number | null;
            /** Is Archived */
            is_archived: boolean;
        };
        /** StageRef */
        StageRef: {
            /** Id */
            id: string;
            /** Code */
            code: string;
            /** Category */
            category: string;
        };
        /** SubmissionOut */
        SubmissionOut: {
            /** Id */
            id: string;
            /** Application Id */
            application_id: string;
            /**
             * Channel
             * @enum {string}
             */
            channel: "manual" | "extension" | "auto";
            /**
             * Submitted At
             * Format: date-time
             */
            submitted_at: string;
            /** Documents */
            documents: {
                [key: string]: unknown;
            }[];
            /** Answers */
            answers: {
                [key: string]: unknown;
            }[];
            /** Note */
            note: string;
            /** Details */
            details?: {
                [key: string]: unknown;
            };
            /** Undone At */
            undone_at: string | null;
        };
        /** TemplateCheck */
        TemplateCheck: {
            /** Problems */
            problems: components["schemas"]["TemplateProblem"][];
            /** Preview Html */
            preview_html: string;
        };
        /** TemplateIn */
        TemplateIn: {
            /** Html */
            html: string;
            /**
             * Filename
             * @default
             */
            filename?: string;
        };
        /** TemplateOut */
        TemplateOut: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "sections" | "letter";
            /** Custom */
            custom: boolean;
            /** Filename */
            filename: string;
            /** Html */
            html: string;
            /** Preview Html */
            preview_html: string;
            /** Updated At */
            updated_at: string | null;
        };
        /** TemplateProblem */
        TemplateProblem: {
            /** Code */
            code: string;
            /** Message */
            message: string;
            /** Wcag */
            wcag: string;
        };
        /** TokenOut */
        TokenOut: {
            /** Id */
            id: string;
            /** Name */
            name: string;
            /**
             * Kind
             * @constant
             */
            kind: "extension";
            /** Prefix */
            prefix: string;
            /** Scopes */
            scopes: ("applications:read" | "applications:write" | "submissions:write" | "profiles:read")[];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Expires At */
            expires_at: string | null;
            /** Last Used At */
            last_used_at: string | null;
            /** Revoked At */
            revoked_at: string | null;
        };
        /** Tokens */
        Tokens: {
            /** Items */
            items: components["schemas"]["TokenOut"][];
        };
        /** Tracked */
        Tracked: {
            match: components["schemas"]["MatchOut"];
            /** Application Id */
            application_id: string;
        };
        /** WarningResolution */
        WarningResolution: {
            /**
             * Resolution
             * @enum {string}
             */
            resolution: "kept" | "open";
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    health_api_v1_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Health"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    model_status_api_v1_system_model_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelStatus"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    choose_model_api_v1_system_model_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ChooseModel"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelChosen"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    reset_model_api_v1_system_model_delete: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelInUse"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    models_api_v1_system_models_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Models"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    sign_in_api_v1_auth_sign_in_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SignIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Me"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    setup_api_v1_auth_setup_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Setup"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    register_api_v1_auth_register_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Register"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Me"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    forgot_password_api_v1_auth_forgot_password_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ForgotPassword"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    check_reset_api_v1_auth_reset_password_check_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ResetToken"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ResetFor"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    reset_password_api_v1_auth_reset_password_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ResetPassword"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    get_registration_api_v1_system_registration_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Registration"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    set_registration_api_v1_system_registration_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Registration"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Registration"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    list_people_api_v1_people_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["People"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    disable_person_api_v1_people__person_id__disable_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                person_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PersonOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    enable_person_api_v1_people__person_id__enable_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                person_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PersonOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    delete_person_api_v1_people__person_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                person_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    sign_out_api_v1_auth_sign_out_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    me_api_v1_auth_me_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Me"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    update_me_api_v1_auth_me_patch: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MeChanges"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Me"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    list_packs_api_v1_packs_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Packs"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    get_pack_api_v1_packs__key__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                key: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PackOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    list_profiles_api_v1_profiles_get: {
        parameters: {
            query?: {
                pack?: string | null;
                after?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Profiles"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    create_profile_api_v1_profiles_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NewProfile"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProfileOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    get_profile_api_v1_profiles__profile_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                profile_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProfileOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    delete_profile_api_v1_profiles__profile_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                profile_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    update_profile_api_v1_profiles__profile_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                profile_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProfileChanges"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProfileOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    import_profile_api_v1_profiles_import_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_import_profile_api_v1_profiles_import_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProfileOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    duplicate_profile_api_v1_profiles__profile_id__duplicate_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                profile_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["DuplicateProfile"] | null;
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProfileOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    read_profile_again_api_v1_profiles__profile_id__read_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                profile_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProfileOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    profile_source_api_v1_profiles__profile_id__source_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                profile_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description The document, as uploaded */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/octet-stream": unknown;
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    list_opportunities_api_v1_opportunities_get: {
        parameters: {
            query?: {
                pack?: string | null;
                after?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Opportunities"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    paste_opportunity_api_v1_opportunities_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Paste"];
            };
        };
        responses: {
            /** @description Pasted before: the same opportunity */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityOut"];
                };
            };
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    get_opportunity_api_v1_opportunities__opportunity_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                opportunity_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    update_opportunity_api_v1_opportunities__opportunity_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                opportunity_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OpportunityChanges"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    extract_opportunity_api_v1_opportunities__opportunity_id__extract_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                opportunity_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunityOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    list_applications_api_v1_applications_get: {
        parameters: {
            query?: {
                pack?: string | null;
                stage?: string | null;
                after?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Applications"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    create_application_api_v1_applications_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NewApplication"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    application_by_url_api_v1_applications_by_url_get: {
        parameters: {
            query: {
                url: string[];
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Lookup"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    get_application_api_v1_applications__application_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                application_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    delete_application_api_v1_applications__application_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                application_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    update_application_api_v1_applications__application_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                application_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ApplicationChanges"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    move_application_api_v1_applications__application_id__stage_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                application_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Move"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ApplicationOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    application_history_api_v1_applications__application_id__history_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                application_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["History"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    list_documents_api_v1_applications__application_id__documents_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                application_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Documents"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    request_document_api_v1_applications__application_id__documents_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                application_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DocumentRequest"];
            };
        };
        responses: {
            /** @description One is already being written: that one */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DocumentOut"];
                };
            };
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DocumentOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    get_document_api_v1_applications__application_id__documents__document_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                application_id: string;
                document_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DocumentOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    list_source_kinds_api_v1_source_kinds_get: {
        parameters: {
            query?: {
                pack?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SourceKinds"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    list_sources_api_v1_sources_get: {
        parameters: {
            query?: {
                pack?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Sources"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    create_source_api_v1_sources_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NewSource"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SourceOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    recognise_source_api_v1_sources_recognise_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SourceAddress"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecognisedSource"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    get_source_api_v1_sources__source_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                source_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SourceOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    delete_source_api_v1_sources__source_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                source_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    update_source_api_v1_sources__source_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                source_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SourceChanges"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SourceOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    fetch_source_api_v1_sources__source_id__fetch_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                source_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SourceOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    list_searches_api_v1_searches_get: {
        parameters: {
            query?: {
                pack?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Searches"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    create_search_api_v1_searches_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NewSearch"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SearchOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    get_search_api_v1_searches__search_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                search_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SearchOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    delete_search_api_v1_searches__search_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                search_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    update_search_api_v1_searches__search_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                search_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SearchChanges"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SearchOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    list_matches_api_v1_matches_get: {
        parameters: {
            query?: {
                status?: string[] | null;
                search_id?: string | null;
                min_score?: number | null;
                after?: string | null;
                limit?: number;
                pack?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Matches"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    update_match_api_v1_matches__match_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                match_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MatchChanges"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MatchOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    track_match_api_v1_matches__match_id__track_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                match_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Tracked"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    todays_briefing_api_v1_briefings_today_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BriefingOut"] | null;
                };
            };
            /** @description Not built yet today */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    build_todays_briefing_api_v1_briefings_today_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BriefingOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    edit_document_api_v1_applications__application_id__documents__document_id__content_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                application_id: string;
                document_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DocumentContent"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DocumentOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    resolve_warning_api_v1_applications__application_id__documents__document_id__warnings__warning_id__post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                application_id: string;
                document_id: string;
                warning_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WarningResolution"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DocumentOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    mark_reviewed_api_v1_applications__application_id__documents__document_id__review_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                application_id: string;
                document_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Reviewed"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DocumentOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    check_document_api_v1_applications__application_id__documents__document_id__check_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                application_id: string;
                document_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DocumentOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    document_pdf_api_v1_applications__application_id__documents__document_id__pdf_get: {
        parameters: {
            query?: {
                download?: boolean;
            };
            header?: never;
            path: {
                application_id: string;
                document_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description The PDF */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/pdf": unknown;
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    document_html_api_v1_applications__application_id__documents__document_id__html_get: {
        parameters: {
            query?: {
                download?: boolean;
            };
            header?: never;
            path: {
                application_id: string;
                document_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description The page */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "text/html": unknown;
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    get_template_api_v1_templates__kind__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                kind: "sections" | "letter";
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TemplateOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    save_template_api_v1_templates__kind__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                kind: "sections" | "letter";
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TemplateIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TemplateOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    reset_template_api_v1_templates__kind__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                kind: "sections" | "letter";
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    default_template_api_v1_templates__kind__default_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                kind: "sections" | "letter";
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TemplateOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    check_template_api_v1_templates__kind__check_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                kind: "sections" | "letter";
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TemplateIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TemplateCheck"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    list_answers_api_v1_answers_get: {
        parameters: {
            query?: {
                pack?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Answers"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    create_answer_api_v1_answers_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NewAnswer"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnswerOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    add_default_answers_api_v1_answers_defaults_post: {
        parameters: {
            query?: {
                pack?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AddedDefaults"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    delete_answer_api_v1_answers__answer_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                answer_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    update_answer_api_v1_answers__answer_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                answer_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AnswerChanges"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnswerOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    application_kit_api_v1_applications__application_id__kit_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                application_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Kit"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    submit_application_api_v1_applications__application_id__submissions_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                application_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NewSubmission"];
            };
        };
        responses: {
            /** @description Recorded already (a reloaded confirmation page) */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SubmissionOut"];
                };
            };
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SubmissionOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    undo_submission_api_v1_submissions__submission_id__undo_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                submission_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SubmissionOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    list_tokens_api_v1_tokens_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Tokens"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    create_token_api_v1_tokens_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NewToken"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CreatedToken"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    revoke_token_api_v1_tokens__token_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                token_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TokenOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    current_token_api_v1_tokens_current_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Caller"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    fill_sheet_api_v1_applications__application_id__fill_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                application_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FillSheet"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    copy_sheet_api_v1_copy_sheet_get: {
        parameters: {
            query?: {
                profile_id?: string | null;
                pack?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CopySheetOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    auto_settings_api_v1_auto_settings_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AutoSettings"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    update_auto_settings_api_v1_auto_settings_patch: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AutoSettingsChanges"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AutoSettings"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    auto_counts_api_v1_auto_counts_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AutoCounts"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    list_runs_api_v1_auto_runs_get: {
        parameters: {
            query?: {
                group?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AutoRuns"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    get_run_api_v1_auto_runs__run_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AutoRunOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    stop_run_api_v1_auto_runs__run_id__stop_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AutoRunOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    retry_run_api_v1_auto_runs__run_id__retry_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AutoRunOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    dismiss_run_api_v1_auto_runs__run_id__dismiss_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AutoRunOut"];
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
    run_screenshot_api_v1_auto_runs__run_id__screenshots__screenshot_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
                screenshot_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description The screenshot */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "image/png": unknown;
                };
            };
            /** @description Client Error */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
            /** @description Server Error */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/problem+json": components["schemas"]["Problem"];
                };
            };
        };
    };
}
