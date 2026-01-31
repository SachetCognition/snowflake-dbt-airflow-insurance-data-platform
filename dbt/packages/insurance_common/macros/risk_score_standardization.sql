{% macro standardize_risk_score(score_column) %}
    case
        when {{ score_column }} is null then null
        when {{ score_column }} < 0 then 0
        when {{ score_column }} > 1 then 1
        else round({{ score_column }}::float, 4)
    end
{% endmacro %}

{% macro calculate_risk_band(score_column) %}
    case
        when {{ score_column }} is null then 'UNKNOWN'
        when {{ score_column }} < 0.3 then 'LOW'
        when {{ score_column }} >= 0.3 and {{ score_column }} < 0.6 then 'MEDIUM'
        when {{ score_column }} >= 0.6 then 'HIGH'
        else 'UNKNOWN'
    end
{% endmacro %}

{% macro calculate_risk_band_with_claims(score_column, claim_frequency_column) %}
    case
        when {{ score_column }} is null then 'UNKNOWN'
        when {{ score_column }} < 0.3 and coalesce({{ claim_frequency_column }}, 0) < 0.5 then 'LOW'
        when {{ score_column }} >= 0.6 or coalesce({{ claim_frequency_column }}, 0) >= 1.0 then 'HIGH'
        else 'MEDIUM'
    end
{% endmacro %}

{% macro normalize_bonus_malus(bonus_malus_column) %}
    case
        when {{ bonus_malus_column }} is null then 0.5
        when {{ bonus_malus_column }} <= 50 then 0.0
        when {{ bonus_malus_column }} >= 350 then 1.0
        else round(({{ bonus_malus_column }} - 50)::float / 300, 4)
    end
{% endmacro %}

{% macro calculate_combined_risk_score(risk_score_column, claim_frequency_column, loss_ratio_column) %}
    round(
        (
            coalesce({{ risk_score_column }}, 0.5) * 0.4 +
            least(coalesce({{ claim_frequency_column }}, 0), 1) * 0.3 +
            least(coalesce({{ loss_ratio_column }}, 0), 1) * 0.3
        ),
        4
    )
{% endmacro %}
