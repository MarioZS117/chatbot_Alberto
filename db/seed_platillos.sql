-- seed_platillos.sql
-- Script idempotente para insertar los platillos usados por el bot
-- Ejecutar después de haber creado las tablas (bot.model.neonbd.ensure_tables())

BEGIN;

-- Pollo salteado con arroz blanco
INSERT INTO platillos (nombre, precio, descripcion)
SELECT 'Pollo salteado con arroz blanco', 120.00, 'Pollo salteado con vegetales y arroz blanco recién hecho.'
WHERE NOT EXISTS (SELECT 1 FROM platillos WHERE nombre = 'Pollo salteado con arroz blanco');

-- Ensalada César
INSERT INTO platillos (nombre, precio, descripcion)
SELECT 'Ensalada César', 80.00, 'Lechuga romana, crutones, queso parmesano y aderezo César casero.'
WHERE NOT EXISTS (SELECT 1 FROM platillos WHERE nombre = 'Ensalada César');

-- Sopa de verduras
INSERT INTO platillos (nombre, precio, descripcion)
SELECT 'Sopa de verduras', 60.00, 'Sopa ligera con una selección de vegetales frescos de temporada.'
WHERE NOT EXISTS (SELECT 1 FROM platillos WHERE nombre = 'Sopa de verduras');

COMMIT;

-- Opcional: listar los platillos insertados
-- SELECT id, nombre, precio, descripcion, creado_en FROM platillos ORDER BY id;
