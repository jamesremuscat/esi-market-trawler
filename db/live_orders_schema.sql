--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'SQL_ASCII';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: live_orders; Type: TABLE; Schema: public; Owner: eve; Tablespace: 
--

CREATE TABLE live_orders (
    orderid bigint NOT NULL,
    typeid bigint,
    regionid bigint,
    price numeric,
    volremaining integer,
    range smallint,
    volentered integer,
    minvolume integer,
    isbid boolean,
    issuedate timestamp without time zone,
    duration smallint,
    locationid bigint,
    expiry timestamp without time zone
);


ALTER TABLE public.live_orders OWNER TO eve;

--
-- Name: live_orders_priKey; Type: CONSTRAINT; Schema: public; Owner: eve; Tablespace: 
--

ALTER TABLE ONLY live_orders
    ADD CONSTRAINT "live_orders_priKey" PRIMARY KEY (orderid);


--
-- Name: cover; Type: INDEX; Schema: public; Owner: eve; Tablespace: 
--

CREATE INDEX cover ON live_orders USING btree (typeid, regionid, isbid);


--
-- Name: expiry; Type: INDEX; Schema: public; Owner: eve; Tablespace: 
--

CREATE INDEX expiry ON live_orders USING btree (expiry);


--
-- Name: live_orders_typeid; Type: INDEX; Schema: public; Owner: eve; Tablespace: 
--

CREATE INDEX live_orders_typeid ON live_orders USING btree (typeid);


--
-- Name: typeandbid; Type: INDEX; Schema: public; Owner: eve; Tablespace: 
--

CREATE INDEX typeandbid ON live_orders USING btree (typeid, isbid);


--
-- Name: typeandregion; Type: INDEX; Schema: public; Owner: eve; Tablespace: 
--

CREATE INDEX typeandregion ON live_orders USING btree (typeid, regionid);

--
-- Name: region; Type: INDEX; Schema: public; Owner: eve; Tablespace: 
--

CREATE INDEX region ON live_orders USING btree (regionid);


--
-- PostgreSQL database dump complete
--

CREATE OR REPLACE FUNCTION _final_median(NUMERIC[])
   RETURNS NUMERIC AS
$$
   SELECT AVG(val)
   FROM (
     SELECT val
     FROM unnest($1) val
     ORDER BY 1
     LIMIT  2 - MOD(array_upper($1, 1), 2)
     OFFSET CEIL(array_upper($1, 1) / 2.0) - 1
   ) sub;
$$
LANGUAGE 'sql' IMMUTABLE;
 
CREATE AGGREGATE median(NUMERIC) (
  SFUNC=array_append,
  STYPE=NUMERIC[],
  FINALFUNC=_final_median,
  INITCOND='{}'
);


CREATE VIEW live_prices AS 
select m.typeid, buy_price, buy_volume, buy_min, buy_max, buy_sd, sell_price, sell_volume, sell_min, sell_max, sell_sd, median_price, (now() at time zone 'UTC') as time  from (
select typeid, median(price) as sell_price,
sum(volRemaining) as sell_volume,
max(price) as sell_max,
min(price) as sell_min,
stddev(price) as sell_sd
from live_orders where isbid=false and expiry >= now()
group by typeid
) s join 
(
select typeid, median(price) as buy_price,
sum(volRemaining) as buy_volume,
max(price) as buy_max,
min(price) as buy_min,
stddev(price) as buy_sd
from live_orders where isbid=true and expiry >= now()
group by typeid
) b on s.typeid=b.typeid join
(
select typeid, median(price) as median_price from live_orders where expiry >= now() group by typeid
) m on m.typeid=s.typeid;

CREATE VIEW regional_prices AS
  SELECT *, (now() at time zone 'UTC') AS time FROM (
    SELECT regionid, typeid, median(price) AS sell_price,
    sum(volRemaining) AS sell_volume,
    max(price) AS sell_max,
    min(price) AS sell_min,
    stddev(price) AS sell_sd
    FROM live_orders WHERE isbid=false AND expiry >= now()
    GROUP BY regionid, typeid
  ) s
  FULL OUTER JOIN
  (
    SELECT regionid, typeid, median(price) AS buy_price,
    sum(volRemaining) AS buy_volume,
    max(price) AS buy_max,
    min(price) AS buy_min,
    stddev(price) AS buy_sd
    FROM live_orders WHERE isbid=true AND expiry >= now()
    GROUP BY regionid, typeid
  ) b 
  USING (regionid, typeid)
  JOIN
  (
    SELECT regionid, typeid, median(price) AS median_price FROM live_orders WHERE expiry >= now() GROUP BY regionid, typeid
  ) m 
  USING (regionid, typeid);

CREATE TABLE trawler_stats ( stats jsonb, time timestamp without time zone);
ALTER TABLE ONLY trawler_stats ADD CONSTRAINT trawler_stats_priKey PRIMARY KEY (time);

