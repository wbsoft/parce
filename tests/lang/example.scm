; scheme example
; convert to html entities
(define (attribute-escape s)
  (string-substitute "\n" "&#10;"
    (string-substitute "\"" "&quot;"
      (string-substitute "&" "&amp;"
        s))))
