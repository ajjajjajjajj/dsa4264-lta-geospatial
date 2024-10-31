Q1 Write a Postgres SQL query that outputs for each day, the top three names with highest
turnover, where turnover = price × volume.

WITH top3_turnover AS (
    SELECT 
        t1.date,
        t2.name,
        t1.ticker,
        (t1.price * t1.volume) AS turnover,
        DENSE_RANK() OVER(
            PARTITION BY t1.date 
            ORDER BY (t1.price * t1.volume) DESC
        ) AS rank 
    FROM t1
    LEFT JOIN t2 
    ON t1.ticker = t2.ticker
)

SELECT date, rank, name, turnover
FROM top3_turnover 
WHERE rank <= 3
ORDER BY date, rank;
